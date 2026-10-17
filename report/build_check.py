# -*- coding: utf-8 -*-
"""RPT_PalmDesk_Check - the model read-back artefact.
Not a deliverable page: it exists so every measure can be compared against a Warehouse value
that was computed independently (SETTLED / App C 42: a capture only means something if you know
what it should show). It also carries the zero-relationship probe in visual form - a dimension
attribute crossed with a fact measure. Identical numbers on every row = no working relationship,
which both validators would pass.
"""
import pbir as P

MID = "<SEMANTIC_MODEL_ID>"
WS  = "<YOUR_WORKSPACE>"
SM  = "SM_PalmDesk"

def card(name, x, y, w, h, items, tab):
    return P.visual(name, "cardVisual", x, y, w, h,
                    roles={"Data": [P.measure(e, m) for e, m in items]}, tab=tab)

def mx(name, x, y, w, h, rows, values, tab):
    return P.visual(name, "matrix", x, y, w, h,
                    roles={"Rows": [P.column(*r) for r in rows],
                           "Values": [P.measure(*v) for v in values]}, tab=tab)

vis = [
  P.textbox("Title", 32, 20, 1216, 46, [
      ("Model check - SM_PalmDesk read-back", {"fontSize": "18pt", "bold": True, "color": "#1B3A2F"})], tab=0),
  P.textbox("Sub", 32, 62, 1216, 34, [
      ("Every value below is compared against the same figure computed directly in WH_PalmDesk. "
       "Synthetic data, fixed seed 20260906.", {"fontSize": "10pt", "color": "#5A6B72"})], tab=1),

  card("KpiPnl", 32, 108, 1216, 150, [
      ("MTM Daily", "MTM (MYR)"),
      ("MTM Daily", "Open Positions"),
      ("Attribution Daily", "Delta MTM (MYR)"),
      ("Attribution Daily", "Attribution Residual (MYR)"),
      ("Attribution Daily", "Max Absolute Unexplained (MYR)"),
      ("Attribution Daily", "Days Outside Tolerance")], tab=2),

  card("KpiRisk", 32, 268, 1216, 150, [
      ("Exposure Daily", "Exposure (MYR)"),
      ("Exposure Daily", "Counterparties in Breach"),
      ("Exposure Daily", "Peak Utilisation"),
      ("Hedge Test Monthly", "Assessments"),
      ("Hedge Test Monthly", "Assessments Effective"),
      ("Physical Contract", "Contracts")], tab=3),

  mx("MxBucket", 32, 432, 600, 250,
     [("Bucket", "bucket_name")],
     [("Attribution Bucket Daily", "Bucket Amount (MYR)")], tab=4),

  mx("MxSegment", 648, 432, 600, 250,
     [("Counterparty", "segment")],
     [("Exposure Daily", "Exposure (MYR)"), ("Exposure Daily", "Counterparties in Breach")], tab=5),
]

# ---------------------------------------------------------------------------------------------
# S3 page: the three calculation groups, each read against a figure computed in the Warehouse
# FIRST (T-SQL over eng.attribution_daily / eng.attribution_bucket_daily joined to ref.calendar,
# 2026-09-07). Computing the expected value before reading the render is the point: a clean-looking
# matrix of a broken calculation group is indistinguishable from a correct one otherwise (App C 42).
# The expected figures are printed on the page so the capture verifies itself.
cg = [
  P.textbox("Title", 32, 20, 1216, 46, [
      ("Calculation groups - read against independently computed Warehouse truth",
       {"fontSize": "18pt", "bold": True, "color": "#1B3A2F"})], tab=0),
  P.textbox("Sub", 32, 62, 1216, 52, [
      ("Bucket over [Bucket Amount (MYR)] must read  New trades -1,239,128 | Price -1,634,890 | "
       "FX 506,667 | Time 3,147,264 | Amendments -314,743 | Unexplained -633,500  (sum = Delta MTM "
       "-168,330).   Time over [Delta MTM (MYR)] must read  Actual -168,330 | Prior Day -2,948,894 | "
       "Current Day 12,632,934 | Day over Day 15,581,829 | MTD 6,249,422 | Rolling 5 21,947,892 | "
       "Rolling 20 6,249,422.   Currency must read  MYR -168,330 | USD -38,080 (at USDMYR 4.420455).",
       {"fontSize": "9pt", "color": "#5A6B72"})], tab=1),

  mx("MxBucketCG", 32, 124, 400, 300,
     [("Attribution Bucket Calculation Group", "Attribution Bucket")],
     [("Attribution Bucket Daily", "Bucket Amount (MYR)")], tab=2),

  mx("MxTimeCG", 448, 124, 400, 300,
     [("Time Calculation Group", "Time Intelligence")],
     [("Attribution Daily", "Delta MTM (MYR)")], tab=3),

  # [USDMYR Rate] is carried alongside deliberately: the USD cell first rendered -38,079 where the
  # Warehouse quotient is -38,079.715775 (which "#,##0" should show as -38,080). A one-unit gap in
  # the last displayed digit is exactly how a real defect hides, so the rate the calculation group
  # actually sees is put on the page rather than assumed. (2026-09-07, S3.)
  mx("MxCcyCG", 864, 124, 384, 300,
     [("Currency Calculation Group", "Currency")],
     [("Attribution Daily", "Delta MTM (MYR)"), ("FX Rate", "USDMYR Rate")], tab=4),

  # The zero-relationship probe, re-run per the kickoff. Six DIFFERENT values summing to Delta MTM
  # is the pass; identical values on every row would mean no working relationship - the one defect
  # both validators are blind to.
  mx("MxZeroRel", 32, 440, 600, 250,
     [("Bucket", "bucket_name")],
     [("Attribution Bucket Daily", "Bucket Amount (MYR)")], tab=5),

  mx("MxSegment2", 648, 440, 600, 250,
     [("Counterparty", "segment")],
     [("Exposure Daily", "Exposure (MYR)")], tab=6),

  # S3 verification card: three of the 32 altText narration measures bound as VISIBLE values.
  # altText itself is not reliably exposed in the service DOM, so binding the measures where they
  # must render is the decisive test of whether they exist in the LIVE model. If the model does not
  # carry them, this visual errors instead of rendering three sentences.
  card("AltProof", 32, 700, 1216, 150, [
      ("MTM Daily", "MTM alt text"),
      ("MTM Daily", "Open Positions alt text"),
      ("Exposure Daily", "Breach count alt text")], tab=7),
]

pg  = P.page("Check", "Check", vis)
pg2 = P.page("CalcGroups", "Calculation groups", cg)
n = P.write("RPT_PalmDesk_Check.Report", [pg, pg2], MID, WS, SM)
print("files written:", n, "visuals:", len(vis) + len(cg))
