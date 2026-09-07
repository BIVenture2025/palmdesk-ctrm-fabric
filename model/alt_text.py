#!/usr/bin/env python3
"""P27 S3 - altText narration measures, one per data-bearing visual (kickoff deliverable 4).

WHY MEASURES AND NOT LITERALS: `validate_pbip.py` counts ALTTEXT_COVERAGE only for
`general.altText` bound to a MEASURE - "a literal on a decorative shape is not alt text"
(the tool's own comment, line 1162; guide §97, CORE_RULES §7.1). A literal would silence the
warning without narrating anything, which is gaming the check rather than passing it.

SCOPE: exactly the 32 data-bearing visuals of P27_PalmDesk - 24 KPI cards and 8 charts/matrices.
Guide §97's own guidance is "narrate the visuals that carry meaning; do not narrate 396"; here
every one of the 32 carries meaning, so all 32 get their own line. Decorative visuals (titles,
nav pills, captions, the disclaimer footer) are deliberately NOT narrated.

Each string states the figure AND its unit, because a screen-reader user gets no axis to read it
against. Values are formatted, never concatenated raw.
"""

# (table the measure lives on, altText measure name, DAX body)
# The name pattern is "<visual> alt text" so the field list stays sortable and obviously derived.
ALT = [
    # ---- page 1, Position & MTM ------------------------------------------------------------
    ("MTM Daily", "MTM alt text",
     '"Book mark-to-market at " & FORMAT ( [Latest Business Date], "yyyy-mm-dd" ) & ": " & FORMAT ( [MTM (MYR)], "#,##0" ) & " MYR."'),
    ("MTM Daily", "Physical MTM alt text",
     '"Physical contracts mark-to-market: " & FORMAT ( [Physical MTM (MYR)], "#,##0" ) & " MYR."'),
    ("MTM Daily", "Futures MTM alt text",
     '"FCPO futures mark-to-market: " & FORMAT ( [Futures MTM (MYR)], "#,##0" ) & " MYR."'),
    ("MTM Daily", "Open Positions alt text",
     '"Open positions on the book: " & FORMAT ( [Open Positions], "#,##0" ) & "."'),
    ("MTM Daily", "Net Position alt text",
     '"Net position, long minus short: " & FORMAT ( [Net Position (MT)], "#,##0.0" ) & " metric tons."'),
    ("FX Rate", "USDMYR Rate alt text",
     '"USDMYR at the latest business day in context: " & FORMAT ( [USDMYR Rate], "0.0000" ) & "."'),
    ("MTM Daily", "MTM trend alt text",
     '"Daily book MTM by product over " & FORMAT ( [Business Days], "0" ) & " business days, ending " & FORMAT ( [MTM (MYR)], "#,##0" ) & " MYR."'),
    ("MTM Daily", "Product table alt text",
     '"MTM and long/short tonnage by product. Net " & FORMAT ( [Net Position (MT)], "#,##0.0" ) & " MT."'),

    # ---- page 2, P&L attribution -----------------------------------------------------------
    ("Attribution Daily", "Delta MTM alt text",
     '"Change in book MTM over the days in context: " & FORMAT ( [Delta MTM (MYR)], "#,##0" ) & " MYR."'),
    ("Attribution Daily", "Sum of Buckets alt text",
     '"The six attribution buckets sum to " & FORMAT ( [Sum of Buckets (MYR)], "#,##0" ) & " MYR."'),
    ("Attribution Daily", "Attribution Residual alt text",
     '"Attribution residual, which must be zero: " & FORMAT ( [Attribution Residual (MYR)], "#,##0.00" ) & " MYR."'),
    ("Attribution Daily", "Max Unexplained alt text",
     '"Largest single-day unexplained amount: " & FORMAT ( [Max Absolute Unexplained (MYR)], "#,##0.00" ) & " MYR."'),
    ("Attribution Daily", "Days Outside Tolerance alt text",
     '"Days above the frozen " & FORMAT ( [Unexplained Tolerance (MYR)], "#,##0.00" ) & " MYR tolerance: " & FORMAT ( [Days Outside Tolerance], "0" ) & "."'),
    ("Attribution Daily", "Realised P&L alt text",
     '"Realised P and L over the days in context: " & FORMAT ( [Realised P&L (MYR)], "#,##0" ) & " MYR."'),
    ("Attribution Bucket Daily", "Bridge alt text",
     '"Waterfall of the six attribution buckets, totalling " & FORMAT ( [Bucket Amount (MYR)], "#,##0" ) & " MYR."'),
    ("Attribution Daily", "Unexplained trend alt text",
     '"Daily unexplained bucket. Largest " & FORMAT ( [Max Absolute Unexplained (MYR)], "#,##0.00" ) & " MYR, " & FORMAT ( [Days Outside Tolerance], "0" ) & " days outside tolerance."'),

    # ---- page 3, Credit exposure -----------------------------------------------------------
    ("Exposure Daily", "Exposure alt text",
     '"Credit exposure net of collateral: " & FORMAT ( [Exposure (MYR)], "#,##0" ) & " MYR."'),
    ("Exposure Daily", "Credit Limit alt text",
     '"Approved credit limit: " & FORMAT ( [Credit Limit (MYR)], "#,##0" ) & " MYR."'),
    ("Exposure Daily", "Utilisation alt text",
     '"Exposure as a share of limit: " & FORMAT ( [Utilisation %], "0.0%" ) & "."'),
    ("Exposure Daily", "Breach count alt text",
     '"Counterparties over their limit: " & FORMAT ( [Counterparties in Breach], "0" ) & "."'),
    ("Exposure Daily", "Amber count alt text",
     '"Counterparties at or above 90 percent utilisation: " & FORMAT ( [Counterparties at 90% or Above], "0" ) & "."'),
    ("Exposure Daily", "ECL alt text",
     '"Expected credit loss: " & FORMAT ( [ECL (MYR)], "#,##0" ) & " MYR."'),
    ("Exposure Daily", "Counterparty table alt text",
     '"Exposure, limit, utilisation and ECL by counterparty. Total " & FORMAT ( [Exposure (MYR)], "#,##0" ) & " MYR across " & FORMAT ( [Counterparties], "0" ) & " counterparties."'),
    ("Exposure Daily", "Country chart alt text",
     '"Credit exposure by counterparty country, totalling " & FORMAT ( [Exposure (MYR)], "#,##0" ) & " MYR."'),

    # ---- page 4, Hedge effectiveness -------------------------------------------------------
    ("Hedge Test Monthly", "Assessments alt text",
     '"Relationship-months assessed: " & FORMAT ( [Assessments], "0" ) & "."'),
    ("Hedge Test Monthly", "Assessments Effective alt text",
     '"Assessed months passing the dollar-offset test: " & FORMAT ( [Assessments Effective], "0" ) & "."'),
    ("Hedge Test Monthly", "Assessments Failing alt text",
     '"Assessed relationship-months that failed: " & FORMAT ( [Assessments Failing], "0" ) & "."'),
    ("Hedge Test Monthly", "Hedge Pass Rate alt text",
     '"Share of assessed relationship-months that passed: " & FORMAT ( [Hedge Pass Rate], "0.0%" ) & "."'),
    ("Hedge Test Monthly", "Ineffectiveness alt text",
     '"Ineffectiveness to profit or loss: " & FORMAT ( [Ineffectiveness to P&L (MYR)], "#,##0" ) & " MYR."'),
    ("Hedge Test Monthly", "OCI Closing alt text",
     '"Cash flow hedge reserve in OCI: " & FORMAT ( [OCI Closing (MYR)], "#,##0" ) & " MYR."'),
    ("Hedge Test Monthly", "Hedge table alt text",
     '"Dollar offset, prospective R squared and ineffectiveness by month and relationship. " & FORMAT ( [Assessments Effective], "0" ) & " of " & FORMAT ( [Assessments], "0" ) & " pass."'),
    ("Hedge Test Monthly", "Offset chart alt text",
     '"Average dollar-offset ratio by month. Window average " & FORMAT ( [Dollar Offset], "0.0000" ) & "."'),
]

# visual name -> (table, altText measure name), consumed by 06_Report/build_report.py
VISUAL_ALT = {
    ("Position", "K1"): ("MTM Daily", "MTM alt text"),
    ("Position", "K2"): ("MTM Daily", "Physical MTM alt text"),
    ("Position", "K3"): ("MTM Daily", "Futures MTM alt text"),
    ("Position", "K4"): ("MTM Daily", "Open Positions alt text"),
    ("Position", "K5"): ("MTM Daily", "Net Position alt text"),
    ("Position", "K6"): ("FX Rate", "USDMYR Rate alt text"),
    ("Position", "TrendMtm"): ("MTM Daily", "MTM trend alt text"),
    ("Position", "MxProduct"): ("MTM Daily", "Product table alt text"),
    ("Attribution", "K1"): ("Attribution Daily", "Delta MTM alt text"),
    ("Attribution", "K2"): ("Attribution Daily", "Sum of Buckets alt text"),
    ("Attribution", "K3"): ("Attribution Daily", "Attribution Residual alt text"),
    ("Attribution", "K4"): ("Attribution Daily", "Max Unexplained alt text"),
    ("Attribution", "K5"): ("Attribution Daily", "Days Outside Tolerance alt text"),
    ("Attribution", "K6"): ("Attribution Daily", "Realised P&L alt text"),
    ("Attribution", "Bridge"): ("Attribution Bucket Daily", "Bridge alt text"),
    ("Attribution", "Unexp"): ("Attribution Daily", "Unexplained trend alt text"),
    ("Credit", "K1"): ("Exposure Daily", "Exposure alt text"),
    ("Credit", "K2"): ("Exposure Daily", "Credit Limit alt text"),
    ("Credit", "K3"): ("Exposure Daily", "Utilisation alt text"),
    ("Credit", "K4"): ("Exposure Daily", "Breach count alt text"),
    ("Credit", "K5"): ("Exposure Daily", "Amber count alt text"),
    ("Credit", "K6"): ("Exposure Daily", "ECL alt text"),
    ("Credit", "MxCp"): ("Exposure Daily", "Counterparty table alt text"),
    ("Credit", "ByCountry"): ("Exposure Daily", "Country chart alt text"),
    ("Hedge", "K1"): ("Hedge Test Monthly", "Assessments alt text"),
    ("Hedge", "K2"): ("Hedge Test Monthly", "Assessments Effective alt text"),
    ("Hedge", "K3"): ("Hedge Test Monthly", "Assessments Failing alt text"),
    ("Hedge", "K4"): ("Hedge Test Monthly", "Hedge Pass Rate alt text"),
    ("Hedge", "K5"): ("Hedge Test Monthly", "Ineffectiveness alt text"),
    ("Hedge", "K6"): ("Hedge Test Monthly", "OCI Closing alt text"),
    ("Hedge", "MxHedge"): ("Hedge Test Monthly", "Hedge table alt text"),
    ("Hedge", "OffsetByMonth"): ("Hedge Test Monthly", "Offset chart alt text"),
}


def build_alt_measures(tag):
    """Returns {table: [tmdl measure block, ...]} to merge into measures.build_measures()."""
    out = {}
    for table, name, dax in ALT:
        block = (f"\tmeasure '{name}' = {dax}\n"
                 f"\t\tisHidden\n"
                 f"\t\tlineageTag: {tag(table, 'alt', name)}")
        out.setdefault(table, []).append(block)
    return out
