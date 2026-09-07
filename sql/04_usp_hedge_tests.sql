CREATE PROCEDURE eng.usp_hedge_tests
AS
BEGIN
    SET NOCOUNT ON;
    TRUNCATE TABLE eng.hedge_test_monthly;
    TRUNCATE TABLE eng.w_hedge;

    -- 1. prospective regression on the 24-month history: item dFV on instrument dFV (monthly changes)
    INSERT INTO eng.w_hedge (hedge_rel_id, slope, r2)
    SELECT h.hedge_rel_id,
           ROUND((s.n * s.sxy - s.sx * s.sy) / (s.n * s.sxx - s.sx * s.sx), 4),
           ROUND(((s.n * s.sxy - s.sx * s.sy) * (s.n * s.sxy - s.sx * s.sy)) / ((s.n * s.sxx - s.sx * s.sx) * (s.n * s.syy - s.sy * s.sy)), 4)
    FROM trd.hedge_relationship h
    JOIN (
        SELECT z.hedge_rel_id, COUNT(*) AS n, SUM(z.x) AS sx, SUM(z.y) AS sy, SUM(z.x * z.x) AS sxx, SUM(z.x * z.y) AS sxy, SUM(z.y * z.y) AS syy
        FROM (
            SELECT h.hedge_rel_id,
                   CAST(-h.designated_lots * 25 * (c1.price - c0.price) AS DECIMAL(20,2)) AS x,
                   CAST(CASE WHEN h.product_code = 'CPO' THEN h.forecast_qty_mt * (c1.price - c0.price)
                             ELSE h.forecast_qty_mt * (p1.price * u1.price - p0.price * u0.price) END AS DECIMAL(30,11)) AS y
            FROM trd.hedge_relationship h
            JOIN (SELECT month_key, price, ROW_NUMBER() OVER (ORDER BY month_key) AS rn FROM mkt.monthly_history WHERE series = 'CPO') c1 ON 1 = 1
            JOIN (SELECT month_key, price, ROW_NUMBER() OVER (ORDER BY month_key) AS rn FROM mkt.monthly_history WHERE series = 'CPO') c0 ON c0.rn = c1.rn - 1
            JOIN mkt.monthly_history p1 ON p1.series = h.product_code AND p1.month_key = c1.month_key
            JOIN mkt.monthly_history p0 ON p0.series = h.product_code AND p0.month_key = c0.month_key
            JOIN mkt.monthly_history u1 ON u1.series = 'USDMYR' AND u1.month_key = c1.month_key
            JOIN mkt.monthly_history u0 ON u0.series = 'USDMYR' AND u0.month_key = c0.month_key
        ) z GROUP BY z.hedge_rel_id
    ) s ON s.hedge_rel_id = h.hedge_rel_id;

    UPDATE eng.w_hedge SET prospective = CASE WHEN slope BETWEEN -1.25 AND -0.80 AND r2 >= 0.80 THEN 1 ELSE 0 END;

    -- 2. base fair values at designation, de minimis floor
    TRUNCATE TABLE eng.w_req;
    INSERT INTO eng.w_req (req_kind, kind, id, product_code, curve_date, tau)
    SELECT 'H', 'D', h.hedge_rel_id, h.product_code, h.designation_date,
           DATEDIFF(day, h.designation_date, DATEFROMPARTS(CAST(LEFT(h.forecast_month, 4) AS INT), CAST(RIGHT(h.forecast_month, 2) AS INT), 15))
    FROM trd.hedge_relationship h;
    EXEC eng.usp_price_requests '2026-12-31';
    UPDATE w SET
        base_item = ROUND(CAST(CAST(h.forecast_qty_mt AS DECIMAL(15,3)) * CAST(r.price AS DECIMAL(15,4)) AS DECIMAL(24,7)) * CASE WHEN h.product_code = 'CPO' THEN CAST(1.000000 AS DECIMAL(12,6)) ELSE f.rate END, 2),
        base_instr = ROUND(CAST(CAST(-h.designated_lots * 25 AS DECIMAL(15,3)) * CAST(ROUND(c.price, 4) AS DECIMAL(15,4)) AS DECIMAL(24,7)) * CAST(1.000000 AS DECIMAL(12,6)), 2),
        closeout = (SELECT MAX(k.biz_date) FROM ref.calendar k WHERE k.month_key = LEFT(CONVERT(VARCHAR(10), DATEADD(month, -1, DATEFROMPARTS(CAST(LEFT(h.forecast_month, 4) AS INT), CAST(RIGHT(h.forecast_month, 2) AS INT), 1)), 120), 7))
    FROM eng.w_hedge w
    JOIN trd.hedge_relationship h ON h.hedge_rel_id = w.hedge_rel_id
    JOIN eng.w_req r ON r.req_kind = 'H' AND r.kind = 'D' AND r.id = h.hedge_rel_id
    LEFT JOIN mkt.fx_rate f ON f.rate_date = h.designation_date AND f.ccy_pair = 'USDMYR'
    JOIN mkt.curve c ON c.product_code = 'CPO' AND c.curve_date = h.designation_date AND c.tenor_month = h.forecast_month AND c.version = 1;
    UPDATE eng.w_hedge SET floor_amt = ROUND(base_item * 0.01, 2), oci_bal = 0, cum_item_prev = 0, cum_instr_prev = 0;

    -- 3. month-end loop (sequential OCI roll-forward)
    DECLARE @me DATE = (SELECT MIN(biz_date) FROM ref.calendar WHERE is_month_end = 1);
    DECLARE @mk CHAR(7);
    DECLARE @next DATE;
    WHILE @me IS NOT NULL
    BEGIN
        SET @mk = LEFT(CONVERT(VARCHAR(10), @me, 120), 7);
        -- reclassification rows: month of sale
        INSERT INTO eng.hedge_test_monthly (month_key, hedge_rel_id, product_code, forecast_month, cum_dfv_item, cum_dfv_instr, dollar_offset, assessed, prospective_slope, prospective_r2, effective, ineffectiveness_pl, oci_open, oci_effective_added, oci_reclassified, oci_close)
        SELECT @mk, h.hedge_rel_id, h.product_code, h.forecast_month, w.cum_item_prev, w.cum_instr_prev, NULL, 0, w.slope, w.r2, w.prospective, 0, w.oci_bal, 0, -w.oci_bal, 0
        FROM eng.w_hedge w JOIN trd.hedge_relationship h ON h.hedge_rel_id = w.hedge_rel_id
        WHERE h.designation_date <= @me AND h.forecast_month = @mk;
        UPDATE w SET oci_bal = 0 FROM eng.w_hedge w JOIN trd.hedge_relationship h ON h.hedge_rel_id = w.hedge_rel_id WHERE h.forecast_month = @mk;

        -- measured rows: relationships designated on/before @me whose forecast month is later than @mk
        TRUNCATE TABLE eng.w_req;
        INSERT INTO eng.w_req (req_kind, kind, id, product_code, curve_date, tau)
        SELECT 'H', 'M', h.hedge_rel_id, h.product_code, @me,
               DATEDIFF(day, @me, DATEFROMPARTS(CAST(LEFT(h.forecast_month, 4) AS INT), CAST(RIGHT(h.forecast_month, 2) AS INT), 15))
        FROM trd.hedge_relationship h WHERE h.designation_date <= @me AND h.forecast_month > @mk;
        EXEC eng.usp_price_requests '2026-12-31';

        -- instrument pricing date: frozen at close-out once closed (a variable inside a JOIN predicate is rejected in distributed mode, so stage it)
        UPDATE eng.w_hedge SET price_date = CASE WHEN @me < closeout THEN @me ELSE closeout END;
        TRUNCATE TABLE eng.w_hedge_m;
        INSERT INTO eng.w_hedge_m (hedge_rel_id, ci, cin)
        SELECT h.hedge_rel_id,
               ROUND(CAST(CAST(h.forecast_qty_mt AS DECIMAL(15,3)) * CAST(r.price AS DECIMAL(15,4)) AS DECIMAL(24,7)) * CASE WHEN h.product_code = 'CPO' THEN CAST(1.000000 AS DECIMAL(12,6)) ELSE f.rate END, 2) - w.base_item,
               ROUND(CAST(CAST(-h.designated_lots * 25 AS DECIMAL(15,3)) * CAST(ROUND(c.price, 4) AS DECIMAL(15,4)) AS DECIMAL(24,7)) * CAST(1.000000 AS DECIMAL(12,6)), 2) - w.base_instr
        FROM trd.hedge_relationship h
        JOIN eng.w_hedge w ON w.hedge_rel_id = h.hedge_rel_id
        JOIN eng.w_req r ON r.req_kind = 'H' AND r.kind = 'M' AND r.id = h.hedge_rel_id
        LEFT JOIN mkt.fx_rate f ON f.rate_date = @me AND f.ccy_pair = 'USDMYR'
        JOIN mkt.curve c ON c.product_code = 'CPO' AND c.tenor_month = h.forecast_month AND c.curve_date = w.price_date AND c.version = 1
        -- version 1 = the version published on the pricing date itself (a restatement is published later by definition)
        WHERE h.designation_date <= @me AND h.forecast_month > @mk;

        UPDATE m SET
            assessed = CASE WHEN ABS(m.ci) >= w.floor_amt THEN 1 ELSE 0 END,
            ratio = CASE WHEN ABS(m.ci) >= w.floor_amt THEN ROUND(m.cin / m.ci, 4) ELSE NULL END
        FROM eng.w_hedge_m m JOIN eng.w_hedge w ON w.hedge_rel_id = m.hedge_rel_id;
        UPDATE m SET effective = CASE WHEN w.prospective = 1 AND (m.assessed = 0 OR ABS(m.ratio) BETWEEN 0.80 AND 1.25) THEN 1 ELSE 0 END
        FROM eng.w_hedge_m m JOIN eng.w_hedge w ON w.hedge_rel_id = m.hedge_rel_id;
        -- lower-of: effective cumulative = instrument change capped at the item change
        UPDATE m SET eff_cum = CASE WHEN m.cin > ABS(m.ci) THEN ABS(m.ci) WHEN m.cin < -ABS(m.ci) THEN -ABS(m.ci) ELSE m.cin END FROM eng.w_hedge_m m;
        UPDATE m SET oci_add = CASE WHEN m.effective = 1 THEN m.eff_cum - w.oci_bal ELSE 0 - w.oci_bal END,
                     d_instr = m.cin - w.cum_instr_prev
        FROM eng.w_hedge_m m JOIN eng.w_hedge w ON w.hedge_rel_id = m.hedge_rel_id;

        INSERT INTO eng.hedge_test_monthly (month_key, hedge_rel_id, product_code, forecast_month, cum_dfv_item, cum_dfv_instr, dollar_offset, assessed, prospective_slope, prospective_r2, effective, ineffectiveness_pl, oci_open, oci_effective_added, oci_reclassified, oci_close)
        SELECT @mk, h.hedge_rel_id, h.product_code, h.forecast_month, m.ci, m.cin, m.ratio, m.assessed, w.slope, w.r2, m.effective,
               m.d_instr - m.oci_add, w.oci_bal, m.oci_add, 0, w.oci_bal + m.oci_add
        FROM eng.w_hedge_m m JOIN eng.w_hedge w ON w.hedge_rel_id = m.hedge_rel_id JOIN trd.hedge_relationship h ON h.hedge_rel_id = m.hedge_rel_id;

        UPDATE w SET oci_bal = w.oci_bal + m.oci_add, cum_item_prev = m.ci, cum_instr_prev = m.cin
        FROM eng.w_hedge w JOIN eng.w_hedge_m m ON m.hedge_rel_id = w.hedge_rel_id;

        -- self-referencing assignment (SET @me = (SELECT ... > @me)) is rejected in distributed mode: stage through @next
        SET @next = (SELECT MIN(biz_date) FROM ref.calendar WHERE is_month_end = 1 AND biz_date > @me);
        SET @me = @next;
    END
END
