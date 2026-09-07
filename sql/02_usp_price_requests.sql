CREATE PROCEDURE eng.usp_price_requests @as_of DATE
AS
BEGIN
    SET NOCOUNT ON;
    -- Curve points for every (product, curve_date) referenced by eng.w_req, using the latest version
    -- published on or before @as_of. Point tenor = days from curve_date to the 15th of the tenor month.
    TRUNCATE TABLE eng.w_pt;
    INSERT INTO eng.w_pt (product_code, curve_date, t, price)
    SELECT c.product_code, c.curve_date,
           DATEDIFF(day, c.curve_date, DATEFROMPARTS(CAST(LEFT(c.tenor_month, 4) AS INT), CAST(RIGHT(c.tenor_month, 2) AS INT), 15)),
           c.price
    FROM mkt.curve c
    JOIN (SELECT product_code, curve_date, MAX(version) AS v
          FROM mkt.curve
          WHERE published_at <= @as_of
            AND EXISTS (SELECT 1 FROM eng.w_req r WHERE r.product_code = mkt.curve.product_code AND r.curve_date = mkt.curve.curve_date)
          GROUP BY product_code, curve_date) m
      ON m.product_code = c.product_code AND m.curve_date = c.curve_date AND m.v = c.version;
    -- bracketing points
    UPDATE eng.w_req SET
        t0 = (SELECT MAX(p.t) FROM eng.w_pt p WHERE p.product_code = eng.w_req.product_code AND p.curve_date = eng.w_req.curve_date AND p.t <= eng.w_req.tau),
        t1 = (SELECT MIN(p.t) FROM eng.w_pt p WHERE p.product_code = eng.w_req.product_code AND p.curve_date = eng.w_req.curve_date AND p.t >= eng.w_req.tau);
    -- linear interpolation on days, flat beyond both ends, rounded to 4 dp (same rule as replay.py P())
    UPDATE w SET price =
        CASE WHEN w.t0 IS NULL THEN ROUND(hi.price, 4)
             WHEN w.t1 IS NULL THEN ROUND(lo.price, 4)
             WHEN w.t0 = w.t1 THEN ROUND(lo.price, 4)
             ELSE ROUND((lo.price * (w.t1 - w.tau) + hi.price * (w.tau - w.t0)) / (w.t1 - w.t0), 4) END
    FROM eng.w_req w
    LEFT JOIN eng.w_pt lo ON lo.product_code = w.product_code AND lo.curve_date = w.curve_date AND lo.t = w.t0
    LEFT JOIN eng.w_pt hi ON hi.product_code = w.product_code AND hi.curve_date = w.curve_date AND hi.t = w.t1;
END
