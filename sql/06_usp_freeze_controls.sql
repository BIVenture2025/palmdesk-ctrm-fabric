CREATE PROCEDURE eng.usp_freeze_controls
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @ts DATETIME2(0) = SYSUTCDATETIME();
    DECLARE @last DATE = (SELECT MAX(biz_date) FROM ref.calendar);
    TRUNCATE TABLE eng.control_total;
    INSERT INTO eng.control_total (control_name, biz_date, dim_key, value_num, value_txt, basis, frozen_at)
    SELECT 'MTM_TOTAL_DAY120', @last, NULL, SUM(mtm_myr), NULL, 'SUM(eng.mtm_daily.mtm_myr) WHERE biz_date = last calendar day; one row per open physical contract (open qty > 0, version OPEN as-of) and open futures trade (close_date null or > d)', @ts FROM eng.mtm_daily WHERE biz_date = @last;
    INSERT INTO eng.control_total (control_name, biz_date, dim_key, value_num, value_txt, basis, frozen_at)
    SELECT 'N_POSITIONS_DAY120', @last, NULL, COUNT(*), NULL, 'COUNT(*) FROM eng.mtm_daily WHERE biz_date = last calendar day', @ts FROM eng.mtm_daily WHERE biz_date = @last;
    INSERT INTO eng.control_total (control_name, biz_date, dim_key, value_num, value_txt, basis, frozen_at)
    SELECT 'NET_POSITION_MT_DAY120', @last, product_code + '|' + ISNULL(tenor_month, 'PHYS'), SUM(s * qty), NULL, 'SUM(s*qty) FROM eng.mtm_daily WHERE biz_date = last day GROUP BY product_code, tenor_month (futures) / PHYS (physical contracts); MT, long positive', @ts FROM eng.mtm_daily WHERE biz_date = @last GROUP BY product_code, ISNULL(tenor_month, 'PHYS');
    INSERT INTO eng.control_total (control_name, biz_date, dim_key, value_num, value_txt, basis, frozen_at)
    SELECT 'DAYS_SUM_BUCKETS_EQ_DMTM', NULL, NULL, SUM(CASE WHEN sum_b = d_mtm THEN 1 ELSE 0 END), CAST(COUNT(*) AS VARCHAR(10)) + ' days run', 'COUNT of eng.attribution_daily rows where b1+..+b6 = mtm_close - mtm_open exactly (DECIMAL(19,2))', @ts FROM eng.attribution_daily;
    INSERT INTO eng.control_total (control_name, biz_date, dim_key, value_num, value_txt, basis, frozen_at)
    SELECT 'UNEXPLAINED_TOLERANCE_MYR', NULL, NULL, MAX(ABS(b6)), NULL, 'MAX(ABS(b6)) over eng.attribution_daily EXCLUDING the three engineered mispricing dates (2026-04-15, 2026-06-08, 2026-07-28); frozen from the clean replay, P24 rule; the health control is ABS(b6) <= this on every non-engineered day', @ts FROM eng.attribution_daily WHERE biz_date NOT IN ('2026-04-15', '2026-06-08', '2026-07-28');
    INSERT INTO eng.control_total (control_name, biz_date, dim_key, value_num, value_txt, basis, frozen_at)
    SELECT 'UNEXPLAINED_ENGINEERED', a.biz_date, a.ref, a.b6, NULL, 'eng.attribution_trade.b6 for the three contracts whose booked price != confirmed price, on their trade date (bucket 1 valued at the confirmed price, MTM at the booked price)', @ts FROM eng.attribution_trade a WHERE a.ref IN ('PC00102', 'PC00270', 'PC00430') AND a.b6 <> 0;
    INSERT INTO eng.control_total (control_name, biz_date, dim_key, value_num, value_txt, basis, frozen_at)
    SELECT 'FIRST_BREACH', x.first_breach, CAST(x.cp_id AS VARCHAR(10)), e.exposure, e.band + ' util ' + CAST(e.utilisation AS VARCHAR(20)), 'MIN(biz_date) per cp_id in eng.exposure_daily WHERE band = BREACH; exposure = mtm_net + ar_open + unbilled + delivery_risk - collateral on that date; CP 3 = engineered MTM route, CP 18 = engineered ageing route, others organic', @ts
    FROM (SELECT cp_id, MIN(biz_date) AS first_breach FROM eng.exposure_daily WHERE band = 'BREACH' GROUP BY cp_id) x
    JOIN eng.exposure_daily e ON e.cp_id = x.cp_id AND e.biz_date = x.first_breach;
    INSERT INTO eng.control_total (control_name, biz_date, dim_key, value_num, value_txt, basis, frozen_at)
    SELECT 'HEDGE_FAIL', NULL, CAST(hedge_rel_id AS VARCHAR(10)) + '|' + month_key, dollar_offset, 'ineffectiveness ' + CAST(ineffectiveness_pl AS VARCHAR(30)), 'eng.hedge_test_monthly rows with assessed = 1 AND effective = 0; dollar-offset = cumulative dFV instrument / cumulative dFV item since designation, band 0.80-1.25', @ts FROM eng.hedge_test_monthly WHERE assessed = 1 AND effective = 0;
    INSERT INTO eng.control_total (control_name, biz_date, dim_key, value_num, value_txt, basis, frozen_at)
    SELECT 'REALISED_TOTAL', NULL, NULL, SUM(realised), NULL, 'SUM(eng.attribution_daily.realised): actualisations at actual price x (1 + quality adj) vs booked price on recorded_date, plus futures close-outs', @ts FROM eng.attribution_daily;
    INSERT INTO eng.control_total (control_name, biz_date, dim_key, value_num, value_txt, basis, frozen_at)
    SELECT 'SOURCE_ROWS', NULL, t, n, NULL, 'COUNT(*) per source table after load; must equal 01_Source/out/manifest.json', @ts FROM (
        SELECT 'ref.calendar' AS t, COUNT(*) AS n FROM ref.calendar UNION ALL SELECT 'ref.product', COUNT(*) FROM ref.product UNION ALL SELECT 'ref.counterparty', COUNT(*) FROM ref.counterparty
        UNION ALL SELECT 'ref.credit_limit', COUNT(*) FROM ref.credit_limit UNION ALL SELECT 'ref.collateral', COUNT(*) FROM ref.collateral UNION ALL SELECT 'ref.ecl_rate', COUNT(*) FROM ref.ecl_rate
        UNION ALL SELECT 'trd.physical_contract', COUNT(*) FROM trd.physical_contract UNION ALL SELECT 'trd.contract_version', COUNT(*) FROM trd.contract_version UNION ALL SELECT 'trd.futures_trade', COUNT(*) FROM trd.futures_trade
        UNION ALL SELECT 'trd.hedge_relationship', COUNT(*) FROM trd.hedge_relationship UNION ALL SELECT 'ops.actualisation', COUNT(*) FROM ops.actualisation UNION ALL SELECT 'ops.invoice', COUNT(*) FROM ops.invoice
        UNION ALL SELECT 'ops.payment', COUNT(*) FROM ops.payment UNION ALL SELECT 'mkt.curve', COUNT(*) FROM mkt.curve UNION ALL SELECT 'mkt.fx_rate', COUNT(*) FROM mkt.fx_rate UNION ALL SELECT 'mkt.monthly_history', COUNT(*) FROM mkt.monthly_history) s;
END
