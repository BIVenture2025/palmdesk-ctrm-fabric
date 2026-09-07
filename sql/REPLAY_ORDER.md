# WH_PalmDesk — replay order (Prod replay in Session 3 follows this exactly)

Each `CREATE SCHEMA` alone in its batch; each `CREATE PROCEDURE` alone in its batch; DDL never mixed with result-returning SELECTs (Gate 1 trap).

1. `000_ddl_sources.sql` — five schemas (one call each) + 16 source tables (one batch). NOTE `mkt.monthly_history.price` is DECIMAL(12,6) (fixed S1 after a 2-dp slip broke the hedge regression).
2. Load `01_Source/out/sql_batches/001..025` verbatim through the DW MCP, ≤ 28 KB each; verify COUNT + checksum against `01_Source/out/manifest.json`.
3. `01_eng_tables.sql`, `01b_hedge_work_tables.sql` (+ `ALTER TABLE eng.w_hedge ADD price_date DATE NULL` if using the pre-fix file), `02_usp_price_requests.sql`, `03_usp_run_eod.sql`, `04_usp_hedge_tests.sql`, `05_usp_run_range_and_controls.sql` (+ `06_usp_freeze_controls.sql`).
4. `EXEC eng.usp_run_range @from_idx, @to_idx` in chunks of ≤ 6 days (the MCP gateway drops the call at ~100 s; the Warehouse keeps running — re-read `eng.run_log` before re-issuing).
5. Restatement: `EXEC eng.usp_run_eod '2026-05-15','2026-05-20',1; ... '2026-05-18' ...; '2026-05-19' ...; EXEC eng.usp_run_eod '2026-05-20','2026-05-20',0;`
6. `EXEC eng.usp_hedge_tests;` then `EXEC eng.usp_freeze_controls;` — compare `eng.control_total` with `07_Exports/E1/control_total_wh.csv`.
