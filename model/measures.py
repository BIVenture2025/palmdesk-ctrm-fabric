# -*- coding: utf-8 -*-
"""P27 SM_PalmDesk measures + calculation groups.
Bucket semantics (b1..b6) were READ OFF eng.usp_run_eod (02_Platform/WH_PalmDesk.Warehouse/
03_usp_run_eod.sql lines 60-101), not from the terminology sheet's prose, which lists
"price - time - FX" while the procedure computes b3 = FX and b4 = time.
"As of" pattern: eng.mtm_daily and eng.exposure_daily are DAILY SNAPSHOTS - summing them across
dates is meaningless, so every stock measure collapses to the latest day_index in filter context.
eng.attribution_daily and eng.hedge_test_monthly are FLOWS and sum across periods normally.
day_index is used instead of DAX time intelligence because ref.calendar holds business days only
(120 rows, Mon-Fri) and is therefore NOT contiguous - DATESYTD and friends would be wrong.
"""

ASOF = "VAR d = MAX ( 'Calendar'[day_index] )\nRETURN\n"

MYR   = "#,##0"
MYR2  = "#,##0.00"
PCT   = "0.0%"
RATIO = "0.0000"
MT    = "#,##0.0"
CNT   = "0"

# (table, name, dax, formatString, description)
M = [
 # ---------------------------------------------------------------- Calendar helpers
 ("Calendar", "Latest Business Date", "MAX ( 'Calendar'[biz_date] )", None,
  "Last business day in the current filter context. The book is valued to this date."),
 ("Calendar", "Business Days", "COUNTROWS ( 'Calendar' )", CNT,
  "Business days in context. The calendar is Mon-Fri only; no public-holiday table exists (declared in the contract)."),

 # ---------------------------------------------------------------- Position and MTM (snapshot)
 ("MTM Daily", "MTM (MYR)",
  ASOF + "CALCULATE ( SUM ( 'MTM Daily'[mtm_myr] ), 'Calendar'[day_index] = d )", MYR,
  "Mark-to-market of the open book at the latest business day in context, in MYR."),
 ("MTM Daily", "MTM Prior Day (MYR)",
  ASOF + "CALCULATE ( SUM ( 'MTM Daily'[mtm_myr] ), REMOVEFILTERS ( 'Calendar' ), 'Calendar'[day_index] = d - 1 )", MYR,
  "MTM on the preceding business day."),
 ("MTM Daily", "MTM Change (MYR)", "[MTM (MYR)] - [MTM Prior Day (MYR)]", MYR,
  "Day-on-day movement in book MTM."),
 ("MTM Daily", "Physical MTM (MYR)",
  ASOF + "CALCULATE ( SUM ( 'MTM Daily'[mtm_myr] ), 'Calendar'[day_index] = d, 'MTM Daily'[kind] = \"P\" )", MYR,
  "MTM of physical contracts only (kind = P)."),
 ("MTM Daily", "Futures MTM (MYR)",
  ASOF + "CALCULATE ( SUM ( 'MTM Daily'[mtm_myr] ), 'Calendar'[day_index] = d, 'MTM Daily'[kind] = \"F\" )", MYR,
  "MTM of FCPO futures lots only (kind = F). Futures are MYR-denominated and carry no FX bucket."),
 ("MTM Daily", "Open Positions",
  ASOF + "CALCULATE ( COUNTROWS ( 'MTM Daily' ), 'Calendar'[day_index] = d )", CNT,
  "Positions on the book at the latest business day in context."),
 ("MTM Daily", "Net Position (MT)",
  ASOF + "CALCULATE ( SUMX ( 'MTM Daily', 'MTM Daily'[s] * 'MTM Daily'[qty] ), 'Calendar'[day_index] = d )", MT,
  "Signed net tonnage: long minus short, in metric tons."),
 ("MTM Daily", "Long Position (MT)",
  ASOF + "CALCULATE ( SUM ( 'MTM Daily'[qty] ), 'Calendar'[day_index] = d, 'MTM Daily'[s] = 1 )", MT,
  "Long tonnage, as a positive magnitude."),
 ("MTM Daily", "Short Position (MT)",
  ASOF + "CALCULATE ( SUM ( 'MTM Daily'[qty] ), 'Calendar'[day_index] = d, 'MTM Daily'[s] = -1 )", MT,
  "Short tonnage, as a positive magnitude."),
 ("MTM Daily", "Restated Positions",
  ASOF + "CALCULATE ( COUNTROWS ( 'MTM Daily' ), 'Calendar'[day_index] = d, 'MTM Daily'[restated] = TRUE () )", CNT,
  "Positions revalued under the CPO 2026-05-15 curve restatement republished on 2026-05-20."),

 # ---------------------------------------------------------------- P&L attribution (flow)
 ("Attribution Daily", "Delta MTM (MYR)", "SUM ( 'Attribution Daily'[d_mtm] )", MYR,
  "Change in book MTM over the days in context. The six buckets explain this figure."),
 ("Attribution Daily", "New Trades (MYR)", "SUM ( 'Attribution Daily'[b1] )", MYR,
  "Bucket 1. Positions with no row on the prior business day, valued at the confirmed price."),
 ("Attribution Daily", "Price (MYR)", "SUM ( 'Attribution Daily'[b2] )", MYR,
  "Bucket 2. Curve move on continuing positions, holding yesterday's tenor fixed, at yesterday's FX."),
 ("Attribution Daily", "FX (MYR)", "SUM ( 'Attribution Daily'[b3] )", MYR,
  "Bucket 3. FX revaluation of continuing physical positions. Futures are MYR and carry none."),
 ("Attribution Daily", "Time (MYR)", "SUM ( 'Attribution Daily'[b4] )", MYR,
  "Bucket 4. One day of carry: yesterday's tenor to today's tenor on today's curve, at today's FX."),
 ("Attribution Daily", "Amendments and Cancellations (MYR)", "SUM ( 'Attribution Daily'[b5] )", MYR,
  "Bucket 5. Positions that left the book, plus the residual on positions whose version or quantity changed."),
 ("Attribution Daily", "Unexplained (MYR)", "SUM ( 'Attribution Daily'[b6] )", MYR2,
  "Bucket 6. Residual on unchanged continuing positions. This is the control the desk watches."),
 ("Attribution Daily", "Sum of Buckets (MYR)", "SUM ( 'Attribution Daily'[sum_b] )", MYR,
  "b1 + b2 + b3 + b4 + b5 + b6 as computed in the Warehouse."),
 ("Attribution Daily", "Attribution Residual (MYR)", "[Sum of Buckets (MYR)] - [Delta MTM (MYR)]", MYR2,
  "Control: must be exactly zero. Frozen at 120 of 120 days on 2026-09-06 09:49:22 UTC."),
 ("Attribution Daily", "Realised P&L (MYR)", "SUM ( 'Attribution Daily'[realised] )", MYR,
  "Realised P&L recorded on the days in context."),
 ("Attribution Daily", "Unexplained Tolerance (MYR)", "0.28", MYR2,
  "Frozen tolerance from VL_PalmDesk (unexplained_tolerance_myr, frozen 2026-09-06 09:49 UTC): the worst non-engineered daily |unexplained| across the 120-day run."),
 ("Attribution Daily", "Max Absolute Unexplained (MYR)",
  "MAXX ( VALUES ( 'Attribution Daily'[biz_date] ), ABS ( CALCULATE ( SUM ( 'Attribution Daily'[b6] ) ) ) )", MYR2,
  "Largest daily |unexplained| in context."),
 ("Attribution Daily", "Days Outside Tolerance",
  "COUNTROWS (\n    FILTER (\n        VALUES ( 'Attribution Daily'[biz_date] ),\n        ABS ( CALCULATE ( SUM ( 'Attribution Daily'[b6] ) ) ) > [Unexplained Tolerance (MYR)]\n    )\n)", CNT,
  "Days whose unexplained bucket exceeds the frozen tolerance. Three are expected, by construction."),
 ("Attribution Daily", "Restated Days",
  "CALCULATE ( COUNTROWS ( 'Attribution Daily' ), 'Attribution Daily'[restated] = TRUE () )", CNT,
  "Days re-run under the curve restatement."),
 ("Attribution Bucket Daily", "Bucket Amount (MYR)", "SUM ( 'Attribution Bucket Daily'[amount] )", MYR,
  "The attribution amount for the bucket(s) in context. Sliced by Bucket, the six values sum to Delta MTM."),

 # ---------------------------------------------------------------- Credit exposure (snapshot)
 ("Exposure Daily", "Exposure (MYR)",
  ASOF + "CALCULATE ( SUM ( 'Exposure Daily'[exposure] ), 'Calendar'[day_index] = d )", MYR,
  "Credit exposure net of collateral at the latest business day in context."),
 ("Exposure Daily", "Credit Limit (MYR)",
  ASOF + "CALCULATE ( SUM ( 'Exposure Daily'[limit_myr] ), 'Calendar'[day_index] = d )", MYR,
  "Approved credit limit. Buyers carry cargo-scale limits, suppliers replacement-cost limits."),
 ("Exposure Daily", "Utilisation %", "DIVIDE ( [Exposure (MYR)], [Credit Limit (MYR)] )", PCT,
  "Exposure divided by limit at the latest business day in context."),
 ("Exposure Daily", "AR Outstanding (MYR)",
  ASOF + "CALCULATE ( SUM ( 'Exposure Daily'[ar_open] ), 'Calendar'[day_index] = d )", MYR,
  "Open accounts receivable."),
 ("Exposure Daily", "ECL (MYR)",
  ASOF + "CALCULATE ( SUM ( 'Exposure Daily'[ecl] ), 'Calendar'[day_index] = d )", MYR,
  "Expected credit loss."),
 ("Exposure Daily", "Counterparties in Breach",
  ASOF + "CALCULATE ( DISTINCTCOUNT ( 'Exposure Daily'[cp_id] ), 'Calendar'[day_index] = d, 'Exposure Daily'[band] = \"BREACH\" )", CNT,
  "Counterparties over their limit at the latest business day in context."),
 ("Exposure Daily", "Counterparties at 90% or Above",
  ASOF + "CALCULATE ( DISTINCTCOUNT ( 'Exposure Daily'[cp_id] ), 'Calendar'[day_index] = d, 'Exposure Daily'[utilisation] >= 0.9 )", CNT,
  "Counterparties at or above 90% utilisation, the amber trigger."),
 ("Exposure Daily", "Peak Utilisation", "MAX ( 'Exposure Daily'[utilisation] )", PCT,
  "Highest utilisation reached over the days in context."),
 ("Exposure Daily", "Breach Days",
  "CALCULATE ( COUNTROWS ( 'Exposure Daily' ), 'Exposure Daily'[band] = \"BREACH\" )", CNT,
  "Counterparty-days spent in breach."),
 ("Counterparty", "Counterparties", "DISTINCTCOUNT ( 'Counterparty'[cp_id] )", CNT,
  "Counterparties in context."),

 # ---------------------------------------------------------------- Hedge effectiveness (flow)
 ("Hedge Test Monthly", "Assessments",
  "CALCULATE ( COUNTROWS ( 'Hedge Test Monthly' ), 'Hedge Test Monthly'[assessed] = TRUE () )", CNT,
  "Relationship-months actually assessed. A month whose cumulative hedged-item change is under 1% of notional is not assessed (the de minimis floor, contract section 6)."),
 ("Hedge Test Monthly", "Assessments Effective",
  "CALCULATE ( COUNTROWS ( 'Hedge Test Monthly' ), 'Hedge Test Monthly'[assessed] = TRUE (), 'Hedge Test Monthly'[effective] = TRUE () )", CNT,
  "Assessed relationship-months that passed the dollar-offset test."),
 ("Hedge Test Monthly", "Assessments Failing", "[Assessments] - [Assessments Effective]", CNT,
  "Assessed relationship-months that failed."),
 ("Hedge Test Monthly", "Hedge Pass Rate", "DIVIDE ( [Assessments Effective], [Assessments] )", PCT,
  "Share of assessed relationship-months that passed."),
 ("Hedge Test Monthly", "Dollar Offset", "AVERAGE ( 'Hedge Test Monthly'[dollar_offset] )", RATIO,
  "Cumulative change in the hedging instrument over the cumulative change in the hedged item. IAS 39 style band: -1.25 to -0.80."),
 ("Hedge Test Monthly", "Prospective Slope", "AVERAGE ( 'Hedge Test Monthly'[prospective_slope] )", RATIO,
  "Regression slope of the prospective effectiveness test."),
 ("Hedge Test Monthly", "Prospective R2", "AVERAGE ( 'Hedge Test Monthly'[prospective_r2] )", RATIO,
  "Regression R-squared of the prospective effectiveness test."),
 ("Hedge Test Monthly", "Ineffectiveness to P&L (MYR)", "SUM ( 'Hedge Test Monthly'[ineffectiveness_pl] )", MYR,
  "Ineffectiveness recognised in profit or loss."),
 ("Hedge Test Monthly", "OCI Closing (MYR)", "SUM ( 'Hedge Test Monthly'[oci_close] )", MYR,
  "Cash flow hedge reserve carried in other comprehensive income at the close of the months in context."),
 ("Hedge Test Monthly", "OCI Reclassified (MYR)", "SUM ( 'Hedge Test Monthly'[oci_reclassified] )", MYR,
  "Amounts recycled out of OCI to profit or loss."),

 # ---------------------------------------------------------------- Contracts and FX
 ("Physical Contract", "Contracts", "COUNTROWS ( 'Physical Contract' )", CNT,
  "Physical contracts in context."),
 ("Physical Contract", "Contract Notional (MT)", "SUM ( 'Physical Contract'[confirmed_qty_mt] )", MT,
  "Confirmed tonnage across the physical contracts in context."),
 ("FX Rate", "USDMYR Rate",
  ASOF + "CALCULATE ( AVERAGE ( 'FX Rate'[rate] ), 'Calendar'[day_index] = d, 'FX Rate'[ccy_pair] = \"USDMYR\" )", RATIO,
  "USDMYR at the latest business day in context."),
]


def measure_tmdl(name, dax, fmt, desc, tag):
    L = []
    if desc:
        for line in desc.split("\n"):
            L.append(f"\t/// {line}")
    body = dax.rstrip("\n")
    if "\n" in body:
        L.append(f"\tmeasure '{name}' =")
        for line in body.split("\n"):
            L.append("\t\t\t" + line if line.strip() else "")
    else:
        L.append(f"\tmeasure '{name}' = {body}")
    if fmt:
        L.append(f"\t\tformatString: {fmt}")
    L.append(f"\t\tlineageTag: {tag}")
    return "\n".join(L)


def build_measures(tagfn):
    out = {}
    for (tbl, name, dax, fmt, desc) in M:
        out.setdefault(tbl, []).append(measure_tmdl(name, dax, fmt, desc, tagfn("measure", tbl, name)))
    return out
