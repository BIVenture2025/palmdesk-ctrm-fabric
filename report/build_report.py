# -*- coding: utf-8 -*-
"""P27 - PalmDesk CTRM Analytics, 4 pages.

Theme: MyLifeInLegoBricks_Theme.json - the engine's stated default (CLAUDE.md standing rule).
P27 has no confirmed brand palette: Serantau Palm Trading Sdn. Bhd. is fictional, and inventing
a "house palette" for it would be inventing a theme. PitchSide Pro Executive (Light) was the
considered alternative and was NOT taken, because the rule sets the default and nothing overrode it.

Every figure on every page is synthetic (fixed seed 20260906). Captions carry the tag of any
term that is not VERIFIED in 00_Plan/TERMINOLOGY.md - the expiry convention above all.
The four organic credit breaches (CP 25, 26, 35, 40) are labelled organic beside the two
engineered ones (CP 3, CP 18). They are not hidden to make the story tidy.
"""
import json, os, sys, pbir as P
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "04_Model"))
from alt_text import VISUAL_ALT

# Shape grepped from a delivered sibling, never written from memory:
#   Projects/07) Business Performance/GlobalEnergy.Report/.../ESGSegBar/visual.json
# general.altText bound to a Measure is the ONLY form validate_pbip counts (guide §97).
def with_alt(vis, page):
    n = 0
    for v in vis:
        key = (page, v["name"])
        if key not in VISUAL_ALT:
            continue
        entity, prop = VISUAL_ALT[key]
        vco = v["visual"].setdefault("visualContainerObjects", {})
        vco.setdefault("general", []).append({"properties": {"altText": {"expr": {"Measure": {
            "Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}}}})
        n += 1
    return n

MID  = "f02c8481-f606-41b8-9026-b09ca1932258"
WS   = "WS_PalmDesk_Dev"
SM   = "SM_PalmDesk"
INK  = "#1B3A5C"
MUTE = "#5A6B72"
DISC = ("Synthetic data. Serantau Palm Trading Sdn. Bhd., its 40 counterparties, all contracts, "
        "curves and FX are fictitious and generated from a fixed seed (20260906) for demonstration. "
        "No real price series is used. FCPO contract specifications are VERIFIED against the Bursa "
        "Malaysia Derivatives product page; the futures expiry rule used here is a generator "
        "convention, not the Bursa rule.")

PAGES = [("Position", "Position & MTM"), ("Attribution", "P&L attribution"),
         ("Credit", "Credit exposure"), ("Hedge", "Hedge effectiveness")]

def kpi(name, table, mname, x, y, w=196, h=92, tab=2000):
    return P.from_component("kpi_card.json", name, x, y, w, h,
                            {"MEASURE_TABLE": table, "MEASURE_NAME": mname}, tab=tab)

def title(name, text):
    return P.from_component("page_title.json", name, 20, 8, 1226, 46, {"PAGE_TITLE": text}, tab=6000)

def nav(name):
    return P.from_component("page_nav_pill.json", name, 20, 58, 1226, 32, {}, tab=5000)

def footer(name):
    return P.from_component("disclaimer_footer.json", name, 20, 676, 1226, 40,
                            {"DISCLAIMER_TEXT": DISC}, tab=0)

def sub(name, text, y=94, h=30):
    return P.textbox(name, 20, y, 1226, h, [(text, {"fontSize": "10pt", "color": MUTE})], tab=5500)

def cap(name, x, y, w, text, h=48):
    return P.textbox(name, x, y, w, h, [(text, {"fontSize": "8pt", "color": MUTE})], tab=100)

def chart(name, vtype, x, y, w, h, cat, vals, tab, series=None, sort=None):
    roles = {"Category": [P.column(*cat)], "Y": [P.measure(*v) for v in vals]}
    if series:
        roles["Series"] = [P.column(*series)]
    return P.visual(name, vtype, x, y, w, h, roles=roles, tab=tab, sort=sort)

def mx(name, x, y, w, h, rows, vals, tab, sort=None):
    return P.visual(name, "matrix", x, y, w, h,
                    roles={"Rows": [P.column(*r) for r in rows],
                           "Values": [P.measure(*v) for v in vals]}, tab=tab, sort=sort)

def desc_by(entity, prop):
    return {"sort": [{"field": {"Measure": {"Expression": {"SourceRef": {"Entity": entity}},
                                            "Property": prop}}, "direction": "Descending"}]}

# ---------------------------------------------------------------- page 1
p1 = [
 title("Title", "Position & mark-to-market"),
 nav("Nav"),
 sub("Sub", "The book closed 2026-08-28 at MYR -168,330 mark-to-market on 449 open positions: a "
            "physical long offset by a larger FCPO short. Net tonnage is short 84,270 MT."),
 kpi("K1", "MTM Daily", "MTM (MYR)", 20, 132),
 kpi("K2", "MTM Daily", "Physical MTM (MYR)", 226, 132),
 kpi("K3", "MTM Daily", "Futures MTM (MYR)", 432, 132),
 kpi("K4", "MTM Daily", "Open Positions", 638, 132),
 kpi("K5", "MTM Daily", "Net Position (MT)", 844, 132),
 kpi("K6", "FX Rate", "USDMYR Rate", 1050, 132),
 P.from_component("line_chart_no_gridline.json", "TrendMtm", 20, 244, 736, 268,
                  {"CATEGORY_TABLE": "Calendar", "CATEGORY_COLUMN": "biz_date",
                   "SERIES_TABLE": "Product", "SERIES_COLUMN": "product_code",
                   "MEASURE_TABLE": "MTM Daily", "MEASURE_NAME": "MTM (MYR)",
                   "SORT_COLUMN": "biz_date",
                   "CHART_TITLE": "Book MTM by product, daily",
                   "TAKEAWAY_SUBTITLE": "The FCPO short carries the book; the physical long moves "
                                        "with the June rally"}, tab=7000),
 mx("MxProduct", 772, 244, 474, 268, [("Product", "product_name")],
    [("MTM Daily", "MTM (MYR)"), ("MTM Daily", "Long Position (MT)"),
     ("MTM Daily", "Short Position (MT)")], tab=7100),
 cap("CapTrend", 20, 516, 736,
     "Daily book MTM by product, valued on the settlement curve published on or before each business "
     "day. The 120 business days run 2026-03-16 to 2026-08-28; there is no public-holiday table, so "
     "the calendar is Mon-Fri only. Days 45-47 carry restated = 1 after the CPO 2026-05-15 curve was "
     "republished on 05-20."),
 cap("CapProd", 772, 516, 474,
     "CPO is bought in MYR and hedged on FCPO (25 MT per lot, MYR 1.00 per MT tick - VERIFIED, "
     "Bursa). RBDPO and PKO sell in USD. Long and short are shown as positive magnitudes."),
 footer("Disc"),
]

# ---------------------------------------------------------------- page 2
p2 = [
 title("Title", "P&L attribution"),
 nav("Nav"),
 sub("Sub", "Over 120 business days the six buckets explain the MYR -168,330 change exactly - the "
            "residual is 0.00 on 120 of 120 days. Three days carry an unexplained amount above the "
            "frozen 0.28 tolerance, and all three are known mispriced trades."),
 kpi("K1", "Attribution Daily", "Delta MTM (MYR)", 20, 132),
 kpi("K2", "Attribution Daily", "Sum of Buckets (MYR)", 226, 132),
 kpi("K3", "Attribution Daily", "Attribution Residual (MYR)", 432, 132),
 kpi("K4", "Attribution Daily", "Max Absolute Unexplained (MYR)", 638, 132),
 kpi("K5", "Attribution Daily", "Days Outside Tolerance", 844, 132),
 kpi("K6", "Attribution Daily", "Realised P&L (MYR)", 1050, 132),
 chart("Bridge", "waterfallChart", 20, 244, 736, 268, ("Bucket", "bucket_name"),
       [("Attribution Bucket Daily", "Bucket Amount (MYR)")], tab=7000),
 chart("Unexp", "columnChart", 772, 244, 474, 268, ("Calendar", "biz_date"),
       [("Attribution Daily", "Unexplained (MYR)")], tab=7100),
 cap("CapBridge", 20, 516, 736,
     "New trades enter at the confirmed price. Price is the curve move holding yesterday's tenor "
     "fixed; Time is one day of carry on today's curve; FX revalues the physical book only - futures "
     "are MYR and carry none. Amendments and cancellations releases the MTM of positions that left "
     "the book. Unexplained is the residual on unchanged positions."),
 cap("CapUnexp", 772, 516, 474,
     "Unexplained by day. Every day sits inside +/-0.28 MYR except 2026-04-15, 2026-06-08 and "
     "2026-07-28 - contracts PC00102, PC00270 and PC00430, booked away from their confirmed price. "
     "The tolerance is frozen in VL_PalmDesk, not fitted to these three days."),
 footer("Disc"),
]

# ---------------------------------------------------------------- page 3
p3 = [
 title("Title", "Credit exposure"),
 nav("Nav"),
 sub("Sub", "Six counterparties breached their limit during the window; four of them did so "
            "organically, with no engineering. At 2026-08-28 four remain in breach."),
 kpi("K1", "Exposure Daily", "Exposure (MYR)", 20, 132),
 kpi("K2", "Exposure Daily", "Credit Limit (MYR)", 226, 132),
 kpi("K3", "Exposure Daily", "Utilisation %", 432, 132),
 kpi("K4", "Exposure Daily", "Counterparties in Breach", 638, 132),
 kpi("K5", "Exposure Daily", "Counterparties at 90% or Above", 844, 132),
 kpi("K6", "Exposure Daily", "ECL (MYR)", 1050, 132),
 mx("MxCp", 20, 244, 736, 268, [("Counterparty", "cp_name")],
    [("Exposure Daily", "Exposure (MYR)"), ("Exposure Daily", "Credit Limit (MYR)"),
     ("Exposure Daily", "Utilisation %"), ("Exposure Daily", "ECL (MYR)")],
    tab=7000, sort=desc_by("Exposure Daily", "Exposure (MYR)")),
 chart("ByCountry", "columnChart", 772, 244, 474, 268, ("Counterparty", "country"),
       [("Exposure Daily", "Exposure (MYR)")], tab=7100,
       sort=desc_by("Exposure Daily", "Exposure (MYR)")),
 cap("CapCp", 20, 516, 736,
     "Exposure is MTM plus open receivables plus unbilled plus delivery risk, net of collateral, "
     "against an approved limit. Engineered: CP 3 (Perusahaan Minyak Sawit Tanjung) breaches from "
     "2026-06-23 on pure MTM, CP 18 (Kandla Vanaspati) from 2026-07-17 on unpaid invoices. "
     "ORGANIC, not engineered: CP 25 (06-04), CP 26 (06-08), CP 35 (06-19), CP 40 (07-13). "
     "A book where only the engineered names ever breach would not be credible."),
 cap("CapCountry", 772, 516, 474,
     "Exposure by counterparty country. Buyers carry cargo-scale limits and suppliers "
     "replacement-cost limits; the rule is applied uniformly, including to the two engineered names."),
 footer("Disc"),
]

# ---------------------------------------------------------------- page 4
p4 = [
 title("Title", "Hedge effectiveness"),
 nav("Nav"),
 sub("Sub", "Twenty-six of 27 assessed relationship-months pass the dollar-offset test. The single "
            "failure is relationship 5 in 2026-06, at -1.4366 against the -1.25 to -0.80 band."),
 kpi("K1", "Hedge Test Monthly", "Assessments", 20, 132),
 kpi("K2", "Hedge Test Monthly", "Assessments Effective", 226, 132),
 kpi("K3", "Hedge Test Monthly", "Assessments Failing", 432, 132),
 kpi("K4", "Hedge Test Monthly", "Hedge Pass Rate", 638, 132),
 kpi("K5", "Hedge Test Monthly", "Ineffectiveness to P&L (MYR)", 844, 132),
 kpi("K6", "Hedge Test Monthly", "OCI Closing (MYR)", 1050, 132),
 mx("MxHedge", 20, 244, 736, 268,
    [("Hedge Test Monthly", "month_key"), ("Hedge Test Monthly", "hedge_rel_id")],
    [("Hedge Test Monthly", "Dollar Offset"), ("Hedge Test Monthly", "Prospective R2"),
     ("Hedge Test Monthly", "Ineffectiveness to P&L (MYR)")], tab=7000),
 chart("OffsetByMonth", "columnChart", 772, 244, 474, 268, ("Hedge Test Monthly", "month_key"),
       [("Hedge Test Monthly", "Dollar Offset")], tab=7100),
 cap("CapHedge", 20, 516, 736,
     "Cash flow hedges of forecast RBDPO sales with FCPO lots. A month whose cumulative hedged-item "
     "change is under 1% of notional is not assessed: the dollar-offset ratio is numerically "
     "meaningless near zero and was producing failures at +/-0.05% of notional. That de minimis "
     "floor is the single methodology amendment on this project and is disclosed, not silent."),
 cap("CapOffset", 772, 516, 474,
     "Dollar offset by month. Relationship 5 carries MYR -1,740,000 of ineffectiveness to profit or "
     "loss in 2026-06; it passes April (-0.8273) and May (-0.9066). Prospective slope -1.0132, "
     "R-squared 0.8555."),
 footer("Disc"),
]

TH = os.path.join(os.path.expanduser("~"), "mnt", "Power BI Automation Engine",
                  "Themes", "MyLifeInLegoBricks_Theme.json")
# guide 143 / validate_pbip THEME_FILE_NAME_MISMATCH: the registered copy's own "name" must equal
# the filename report.json resolves. The source theme in Themes/ is left untouched.
_t = json.load(open(TH, encoding="utf-8-sig"))
_t["name"] = "MyLifeInLegoBricks_Theme.json"
theme = {"name": "MyLifeInLegoBricks_Theme.json", "json": json.dumps(_t, indent=2, ensure_ascii=False)}

_alt = sum(with_alt(v, n) for (n, _d), v in zip(PAGES, [p1, p2, p3, p4]))
print("altText bound to a measure on", _alt, "data visuals")
pages = [P.page(n, d, v) for (n, d), v in zip(PAGES, [p1, p2, p3, p4])]
n = P.write("P27_PalmDesk.Report", pages, MID, WS, SM, theme=theme)
print("files:", n, "pages:", len(pages), "visuals:", sum(len(v) for v in [p1, p2, p3, p4]))


# ---------------------------------------------------------------- the .pbip fallback package
# Schema URL copied from delivered projects 07/12/16 - the segment is /fabric/pbip/, NOT
# /fabric/item/. Power BI Desktop rejects the wrong one outright:
#   "Expected '$schema' property ... to follow patterns:
#    ^https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.[0-9]+.[0-9]+/schema.json$"
# It was written from memory once (2026-09-07) and Desktop caught it; validate_pbip.py now lints it.
PBIP_SCHEMA = ("https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/"
               "1.0.0/schema.json")


def write_pbip(root, report_folder, model_folder, name):
    """Assemble the .pbip package: report bound byPath to a sibling semantic model."""
    import shutil
    os.makedirs(root, exist_ok=True)
    for src, dstname in ((report_folder, os.path.basename(report_folder)),
                         (model_folder, os.path.basename(model_folder))):
        dst = os.path.join(root, dstname)
        os.makedirs(dst, exist_ok=True)
        for r, _, fs in os.walk(src):
            for f in fs:
                sp = os.path.join(r, f)
                dp = os.path.join(dst, os.path.relpath(sp, src))
                os.makedirs(os.path.dirname(dp), exist_ok=True)
                shutil.copyfile(sp, dp)
    pbir = os.path.join(root, os.path.basename(report_folder), "definition.pbir")
    d = json.load(open(pbir))
    d["datasetReference"] = {"byPath": {"path": f"../{os.path.basename(model_folder)}"}}
    with open(pbir, "w") as f:
        json.dump(d, f, indent=2); f.write("\n")
    with open(os.path.join(root, f"{name}.pbip"), "w") as f:
        json.dump({"$schema": PBIP_SCHEMA, "version": "1.0",
                   "artifacts": [{"report": {"path": os.path.basename(report_folder)}}],
                   "settings": {"enableAutoRecovery": True}}, f, indent=2)
        f.write("\n")
    return sum(len(fs) for _, _, fs in os.walk(root))


def write_publish(root, report_folder, name):
    """The DEFAULT package: report-only, bound byConnection to the LIVE SM_PalmDesk.

    F-32: a byPath .pbip can never metadata-match a model the service has rewritten on ingest
    (F-16: pbism 4.0 -> 4.2, database name stripped, CRLF -> LF, +.platform), so Desktop always
    offers to overwrite the live model. This package carries no model at all, so there is nothing
    to reconcile - it opens clean and one Publish sends all four pages.

    S3 note: this assembly was a one-off in S2 and is now owned by the generator, for exactly the
    reason F-31 gives - a hand-made package escapes review and Desktop is its only validator.
    """
    import shutil
    # The device sandbox cannot delete files, so this overwrites in place and then REPORTS any
    # stale file the previous build left behind rather than silently tolerating it (App C 24:
    # a check must say how much it read, and "0 findings" must not look like "0 files read").
    os.makedirs(root, exist_ok=True)
    dst = os.path.join(root, os.path.basename(report_folder))
    written = set()
    for r, _, fs in os.walk(report_folder):
        for f in fs:
            sp = os.path.join(r, f)
            dp = os.path.join(dst, os.path.relpath(sp, report_folder))
            os.makedirs(os.path.dirname(dp), exist_ok=True)
            shutil.copyfile(sp, dp)
            written.add(os.path.relpath(dp, root).replace(os.sep, "/"))
    pbir = os.path.join(dst, "definition.pbir")
    d = json.load(open(pbir, encoding="utf-8"))
    d["datasetReference"] = {"byConnection": {"connectionString": (
        f"Data Source=powerbi://api.powerbi.com/v1.0/myorg/{WS};initial catalog={SM};"
        f"access mode=readonly;integrated security=ClaimsToken;semanticmodelid={MID}")}}
    with open(pbir, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2); f.write("\n")
    with open(os.path.join(root, f"{name}.pbip"), "w", encoding="utf-8") as f:
        json.dump({"$schema": PBIP_SCHEMA, "version": "1.0",
                   "artifacts": [{"report": {"path": os.path.basename(report_folder)}}],
                   "settings": {"enableAutoRecovery": True}}, f, indent=2)
        f.write("\n")
    written.add(f"{name}.pbip")
    on_disk = {os.path.relpath(os.path.join(r, f), root).replace(os.sep, "/")
               for r, _, fs in os.walk(root) for f in fs}
    stale = sorted(on_disk - written - {".gitignore"})
    if stale:
        print(f"  [publish] {len(stale)} STALE file(s) from a previous build, not deleted "
              f"(sandbox cannot delete): {stale}")
    print(f"  [publish] scanned {len(on_disk)} file(s) on disk, wrote {len(written)}")
    return len(on_disk)


if __name__ == "__main__" or True:
    _n = write_pbip("P27_PalmDesk_pbip", "P27_PalmDesk.Report",
                    os.path.join("..", "04_Model", "SM_PalmDesk.SemanticModel"), "P27_PalmDesk")
    print("pbip package (byPath, rebuild-from-scratch):", _n, "files")
    _p = write_publish("P27_PalmDesk_publish", "P27_PalmDesk.Report", "P27_PalmDesk")
    print("publish package (byConnection, DEFAULT):", _p, "files")
