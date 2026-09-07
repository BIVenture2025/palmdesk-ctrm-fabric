CREATE PROCEDURE eng.usp_run_eod @d DATE, @as_of DATE, @restated BIT
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @prev DATE = (SELECT MAX(biz_date) FROM ref.calendar WHERE biz_date < @d);
    DECLARE @run_ts DATETIME2(0) = SYSUTCDATETIME();
    IF @as_of IS NULL SET @as_of = @d;

    -- idempotent: wipe the day
    DELETE FROM eng.mtm_daily WHERE biz_date = @d;
    DELETE FROM eng.attribution_trade WHERE biz_date = @d;
    DELETE FROM eng.attribution_daily WHERE biz_date = @d;
    DELETE FROM eng.exposure_daily WHERE biz_date = @d;
    DELETE FROM eng.run_log WHERE biz_date = @d;

    ------------------------------------------------------------------ 1. open positions at @d
    TRUNCATE TABLE eng.w_pos;
    INSERT INTO eng.w_pos (kind, id, ref, product_code, cp_id, tenor_month, s, qty, k, k_conf, fx, tau, version_no)
    SELECT 'P', c.contract_id, c.contract_ref, c.product_code, c.cp_id, NULL,
           CASE c.side WHEN 'B' THEN 1 ELSE -1 END,
           v.quantity_mt - ISNULL(a.q, 0), v.price, c.confirmed_price,
           CASE c.price_ccy WHEN 'MYR' THEN CAST(1.000000 AS DECIMAL(12,6)) ELSE f.rate END,
           DATEDIFF(day, @d, c.delivery_date), v.version_no
    FROM trd.physical_contract c
    JOIN trd.contract_version v
      ON v.contract_id = c.contract_id
     AND v.version_no = (SELECT MAX(v2.version_no) FROM trd.contract_version v2 WHERE v2.contract_id = c.contract_id AND v2.valid_from <= @d)
    LEFT JOIN (SELECT contract_id, SUM(quantity_mt) AS q FROM ops.actualisation WHERE recorded_date <= @d GROUP BY contract_id) a
      ON a.contract_id = c.contract_id
    LEFT JOIN mkt.fx_rate f ON f.rate_date = @d AND f.ccy_pair = c.price_ccy + 'MYR'
    WHERE c.trade_date <= @d AND v.status = 'OPEN' AND v.quantity_mt - ISNULL(a.q, 0) > 0;

    INSERT INTO eng.w_pos (kind, id, ref, product_code, cp_id, tenor_month, s, qty, k, k_conf, fx, tau, version_no)
    SELECT 'F', t.trade_id, t.trade_ref, 'CPO', NULL, t.contract_month,
           CASE t.side WHEN 'B' THEN 1 ELSE -1 END,
           CAST(t.lots * 25 AS DECIMAL(12,3)), t.price_myr, t.price_myr, CAST(1.000000 AS DECIMAL(12,6)), NULL, 1
    FROM trd.futures_trade t
    WHERE t.trade_date <= @d AND (t.close_date IS NULL OR t.close_date > @d);

    ------------------------------------------------------------------ 2. curve prices: today's tau, and yesterday's tau on today's curve
    TRUNCATE TABLE eng.w_req;
    INSERT INTO eng.w_req (req_kind, kind, id, product_code, curve_date, tau)
    SELECT 'N', kind, id, product_code, @d, tau FROM eng.w_pos WHERE kind = 'P';
    INSERT INTO eng.w_req (req_kind, kind, id, product_code, curve_date, tau)
    SELECT 'O', m.kind, m.id, m.product_code, @d, m.tau
    FROM eng.mtm_daily m JOIN eng.w_pos w ON w.kind = m.kind AND w.id = m.id
    WHERE m.biz_date = @prev AND m.kind = 'P';
    EXEC eng.usp_price_requests @as_of;

    UPDATE w SET curve_price = r.price
    FROM eng.w_pos w JOIN eng.w_req r ON r.req_kind = 'N' AND r.kind = w.kind AND r.id = w.id;
    -- futures: settlement of the contract month, no interpolation
    UPDATE w SET curve_price = ROUND(c.price, 4)
    FROM eng.w_pos w
    JOIN mkt.curve c ON c.product_code = 'CPO' AND c.curve_date = @d AND c.tenor_month = w.tenor_month
     AND c.version = (SELECT MAX(version) FROM mkt.curve c2 WHERE c2.product_code = 'CPO' AND c2.curve_date = @d AND c2.published_at <= @as_of)
    WHERE w.kind = 'F';

    -- MTM = R2( s*Q*(P-K)*F ), computed exactly: (s*Q)*(P-K) -> DECIMAL(24,7), then * F -> DECIMAL(37,13)
    UPDATE eng.w_pos SET mtm_myr = ROUND(CAST(CAST(s * qty AS DECIMAL(15,3)) * CAST(curve_price - k AS DECIMAL(15,4)) AS DECIMAL(24,7)) * fx, 2);

    INSERT INTO eng.mtm_daily (biz_date, kind, id, ref, product_code, cp_id, tenor_month, s, qty, tau, curve_price, contract_price, fx, mtm_myr, version_no, restated)
    SELECT @d, kind, id, ref, product_code, cp_id, tenor_month, s, qty, tau, curve_price, k, fx, mtm_myr, version_no, @restated FROM eng.w_pos;

    ------------------------------------------------------------------ 3. attribution per position
    -- continuing positions
    INSERT INTO eng.attribution_trade (biz_date, kind, id, ref, b1, b2, b3, b4, b5, b6, mtm_open, mtm_close)
    SELECT @d, x.kind, x.id, x.ref, CAST(0 AS DECIMAL(19,2)), x.b2, x.b3, x.b4,
           CASE WHEN x.changed = 1 THEN x.mtm_close - x.mtm_open - x.b2 - x.b3 - x.b4 ELSE 0 END,
           CASE WHEN x.changed = 1 THEN 0 ELSE x.mtm_close - x.mtm_open - x.b2 - x.b3 - x.b4 END,
           x.mtm_open, x.mtm_close
    FROM (
        SELECT w.kind, w.id, w.ref, p.mtm_myr AS mtm_open, w.mtm_myr AS mtm_close,
               CASE WHEN w.version_no <> p.version_no OR w.qty <> p.qty THEN 1 ELSE 0 END AS changed,
               CASE WHEN w.kind = 'P'
                    THEN ROUND(CAST(CAST(p.s * p.qty AS DECIMAL(15,3)) * CAST(o.price - p.curve_price AS DECIMAL(15,4)) AS DECIMAL(24,7)) * p.fx, 2)
                    ELSE ROUND(CAST(CAST(p.s * p.qty AS DECIMAL(15,3)) * CAST(w.curve_price - p.curve_price AS DECIMAL(15,4)) AS DECIMAL(24,7)) * p.fx, 2) END AS b2,
               CASE WHEN w.kind = 'P'
                    THEN ROUND(CAST(CAST(p.s * p.qty AS DECIMAL(15,3)) * CAST(o.price - p.contract_price AS DECIMAL(15,4)) AS DECIMAL(24,7)) * CAST(w.fx - p.fx AS DECIMAL(13,6)), 2)
                    ELSE CAST(0 AS DECIMAL(19,2)) END AS b3,
               CASE WHEN w.kind = 'P'
                    THEN ROUND(CAST(CAST(p.s * p.qty AS DECIMAL(15,3)) * CAST(w.curve_price - o.price AS DECIMAL(15,4)) AS DECIMAL(24,7)) * w.fx, 2)
                    ELSE CAST(0 AS DECIMAL(19,2)) END AS b4
        FROM eng.w_pos w
        JOIN eng.mtm_daily p ON p.biz_date = @prev AND p.kind = w.kind AND p.id = w.id
        LEFT JOIN eng.w_req o ON o.req_kind = 'O' AND o.kind = w.kind AND o.id = w.id
    ) x;

    -- new positions (no row yesterday): bucket 1 at the CONFIRMED price; any booking difference falls to bucket 6
    INSERT INTO eng.attribution_trade (biz_date, kind, id, ref, b1, b2, b3, b4, b5, b6, mtm_open, mtm_close)
    SELECT @d, y.kind, y.id, y.ref, y.b1, 0, 0, 0, 0, y.mtm_myr - y.b1, 0, y.mtm_myr
    FROM (SELECT w.kind, w.id, w.ref, w.mtm_myr,
                 ROUND(CAST(CAST(w.s * w.qty AS DECIMAL(15,3)) * CAST(w.curve_price - w.k_conf AS DECIMAL(15,4)) AS DECIMAL(24,7)) * w.fx, 2) AS b1
          FROM eng.w_pos w
          WHERE NOT EXISTS (SELECT 1 FROM eng.mtm_daily p WHERE p.biz_date = @prev AND p.kind = w.kind AND p.id = w.id)) y;

    -- positions that left the book today (actualised / cancelled / closed out): bucket 5 releases yesterday's MTM
    INSERT INTO eng.attribution_trade (biz_date, kind, id, ref, b1, b2, b3, b4, b5, b6, mtm_open, mtm_close)
    SELECT @d, p.kind, p.id, p.ref, 0, 0, 0, 0, -p.mtm_myr, 0, p.mtm_myr, 0
    FROM eng.mtm_daily p
    WHERE p.biz_date = @prev AND NOT EXISTS (SELECT 1 FROM eng.w_pos w WHERE w.kind = p.kind AND w.id = p.id);

    ------------------------------------------------------------------ 4. realised P&L recorded today
    DECLARE @realised DECIMAL(19,2) = 0;
    SELECT @realised = ISNULL(SUM(x.r), 0)
    FROM (
        SELECT ROUND(CAST(CAST(CASE c.side WHEN 'B' THEN 1 ELSE -1 END * a.quantity_mt AS DECIMAL(15,3))
                          * CAST(a.actual_price * (1 + a.quality_adj_pct) - v.price AS DECIMAL(17,6)) AS DECIMAL(24,9))
                     * CASE c.price_ccy WHEN 'MYR' THEN CAST(1.000000 AS DECIMAL(12,6)) ELSE f.rate END, 2) AS r
        FROM ops.actualisation a
        JOIN trd.physical_contract c ON c.contract_id = a.contract_id
        JOIN trd.contract_version v ON v.contract_id = c.contract_id
         AND v.version_no = (SELECT MAX(v2.version_no) FROM trd.contract_version v2 WHERE v2.contract_id = c.contract_id AND v2.valid_from <= @d)
        LEFT JOIN mkt.fx_rate f ON f.rate_date = @d AND f.ccy_pair = c.price_ccy + 'MYR'
        WHERE a.recorded_date = @d
        UNION ALL
        SELECT ROUND(CAST(CAST(CASE t.side WHEN 'B' THEN 1 ELSE -1 END * t.lots * 25 AS DECIMAL(15,3)) * CAST(t.close_price - t.price_myr AS DECIMAL(15,4)) AS DECIMAL(24,7)) * CAST(1.000000 AS DECIMAL(12,6)), 2)
        FROM trd.futures_trade t WHERE t.close_date = @d
    ) x;

    INSERT INTO eng.attribution_daily (biz_date, mtm_open, mtm_close, d_mtm, b1, b2, b3, b4, b5, b6, sum_b, realised, restated, run_ts)
    SELECT @d, SUM(mtm_open), SUM(mtm_close), SUM(mtm_close) - SUM(mtm_open), SUM(b1), SUM(b2), SUM(b3), SUM(b4), SUM(b5), SUM(b6),
           SUM(b1) + SUM(b2) + SUM(b3) + SUM(b4) + SUM(b5) + SUM(b6), @realised, @restated, @run_ts
    FROM eng.attribution_trade WHERE biz_date = @d;

    ------------------------------------------------------------------ 5. counterparty exposure (staged updates; each term mirrors replay.py)
    INSERT INTO eng.exposure_daily (biz_date, cp_id, mtm_net, ar_open, unbilled, delivery_risk, collateral, exposure, limit_myr, utilisation, band, ecl)
    SELECT @d, cp.cp_id, 0, 0, 0, 0, 0, 0, l.approved_limit_myr, 0, '', 0
    FROM ref.counterparty cp JOIN ref.credit_limit l ON l.cp_id = cp.cp_id;

    UPDATE e SET mtm_net =
        CASE WHEN cp.has_netting = 1
             THEN (SELECT CASE WHEN ISNULL(SUM(w.mtm_myr), 0) > 0 THEN SUM(w.mtm_myr) ELSE 0 END FROM eng.w_pos w WHERE w.cp_id = cp.cp_id)
             ELSE (SELECT ISNULL(SUM(CASE WHEN w.mtm_myr > 0 THEN w.mtm_myr ELSE 0 END), 0) FROM eng.w_pos w WHERE w.cp_id = cp.cp_id) END
    FROM eng.exposure_daily e JOIN ref.counterparty cp ON cp.cp_id = e.cp_id WHERE e.biz_date = @d;

    UPDATE e SET ar_open = ISNULL(o.ar, 0), ecl = ISNULL(o.ecl, 0)
    FROM eng.exposure_daily e
    LEFT JOIN (
        SELECT x.cp_id, SUM(x.open_amt) AS ar, SUM(ROUND(x.open_amt * r.rate, 2)) AS ecl
        FROM (SELECT i.cp_id, i.due_date, cp.grade,
                     i.amount_myr - ISNULL((SELECT SUM(p.amount_myr) FROM ops.payment p WHERE p.invoice_id = i.invoice_id AND p.payment_date <= @d), 0) AS open_amt
              FROM ops.invoice i JOIN ref.counterparty cp ON cp.cp_id = i.cp_id
              WHERE i.side = 'S' AND i.invoice_date <= @d) x
        JOIN ref.ecl_rate r ON r.grade = x.grade
         AND r.ageing_band = CASE WHEN DATEDIFF(day, x.due_date, @d) <= 30 THEN '0-30' WHEN DATEDIFF(day, x.due_date, @d) <= 60 THEN '31-60'
                                  WHEN DATEDIFF(day, x.due_date, @d) <= 90 THEN '61-90' ELSE '90+' END
        WHERE x.open_amt > 0
        GROUP BY x.cp_id) o ON o.cp_id = e.cp_id
    WHERE e.biz_date = @d;

    UPDATE e SET unbilled = ISNULL(u.amt, 0)
    FROM eng.exposure_daily e
    LEFT JOIN (
        SELECT c.cp_id, SUM(ROUND(CAST(CAST(a.quantity_mt AS DECIMAL(15,3)) * CAST(a.actual_price AS DECIMAL(15,4)) AS DECIMAL(24,7))
                                  * CASE c.price_ccy WHEN 'MYR' THEN CAST(1.000000 AS DECIMAL(12,6)) ELSE f.rate END, 2)) AS amt
        FROM ops.actualisation a
        JOIN trd.physical_contract c ON c.contract_id = a.contract_id
        LEFT JOIN mkt.fx_rate f ON f.rate_date = @d AND f.ccy_pair = c.price_ccy + 'MYR'
        WHERE c.side = 'S' AND a.recorded_date <= @d
          AND NOT EXISTS (SELECT 1 FROM ops.invoice i WHERE i.contract_id = a.contract_id AND i.invoice_date <= @d)
        GROUP BY c.cp_id) u ON u.cp_id = e.cp_id
    WHERE e.biz_date = @d;

    UPDATE e SET delivery_risk = ISNULL(dr.amt, 0)
    FROM eng.exposure_daily e
    JOIN ref.counterparty cp ON cp.cp_id = e.cp_id
    LEFT JOIN (SELECT w.cp_id, SUM(ROUND(CAST(CAST(w.qty AS DECIMAL(15,3)) * CAST(w.k AS DECIMAL(15,4)) AS DECIMAL(24,7)) * w.fx, 2)) AS amt
               FROM eng.w_pos w WHERE w.kind = 'P' AND w.s = -1 AND w.tau BETWEEN 0 AND 30 GROUP BY w.cp_id) dr ON dr.cp_id = e.cp_id AND cp.we_deliver_first = 1
    WHERE e.biz_date = @d;

    UPDATE e SET collateral = ISNULL(k.amt, 0)
    FROM eng.exposure_daily e
    LEFT JOIN (SELECT cp_id, SUM(ROUND(amount_myr * (1 - CASE collateral_type WHEN 'LC' THEN 0.10 ELSE 0 END), 2)) AS amt FROM ref.collateral GROUP BY cp_id) k ON k.cp_id = e.cp_id
    WHERE e.biz_date = @d;

    UPDATE eng.exposure_daily SET exposure = mtm_net + ar_open + unbilled + delivery_risk - collateral WHERE biz_date = @d;
    UPDATE eng.exposure_daily SET utilisation = ROUND(exposure / limit_myr, 4) WHERE biz_date = @d;
    UPDATE eng.exposure_daily SET band = CASE WHEN utilisation < 0.75 THEN 'GREEN' WHEN utilisation < 0.90 THEN 'AMBER' WHEN utilisation <= 1.00 THEN 'RED' ELSE 'BREACH' END WHERE biz_date = @d;

    ------------------------------------------------------------------ 6. run log
    INSERT INTO eng.run_log (biz_date, as_of_date, restated, run_ts, n_positions, mtm_close, unexplained)
    SELECT @d, @as_of, @restated, @run_ts, (SELECT COUNT(*) FROM eng.w_pos), a.mtm_close, a.b6
    FROM eng.attribution_daily a WHERE a.biz_date = @d;
END
