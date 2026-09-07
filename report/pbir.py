# -*- coding: utf-8 -*-
"""Minimal PBIR generator for P27.

Schema versions are PINNED to what this tenant accepted on 2026-09-06 (Gate 4, and P26's
delivered report): report 3.3.0, pagesMetadata 1.1.0, page 2.1.0, visualContainer 2.11.0,
versionMetadata 1.0.0 / "2.0.0", definitionProperties 2.0.0.
Every visual's query shape is copied from a working delivered example, never written from memory:
  cardVisual   -> P26 Overview/Kpi          matrix    -> P26 Risk/MxBand
  columnChart  -> P26 Overview/ByService    waterfall -> P07 FinancialPerformance/WaterfallPL
  lineChart    -> P03 APCSupport/ChartAPCTrend        textbox -> P03 APCSupport/Disclaimer
"""
import json, os, re

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
S_VIS  = f"{SCHEMA}/visualContainer/2.11.0/schema.json"
S_PAGE = f"{SCHEMA}/page/2.1.0/schema.json"
S_PAGES= f"{SCHEMA}/pagesMetadata/1.1.0/schema.json"
S_RPT  = f"{SCHEMA}/report/3.3.0/schema.json"
S_VER  = f"{SCHEMA}/versionMetadata/1.0.0/schema.json"
S_PBIR = "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json"

# Visual types that cannot drill, so must not carry drillFilterOtherVisuals (guide 24a).
NO_DRILL = {"tableEx", "textbox", "pageNavigator", "actionButton", "shape", "image", "card"}


def measure(entity, prop):
    return {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
            "queryRef": f"{entity}.{prop}", "nativeQueryRef": prop, "active": True}


def column(entity, prop):
    return {"field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
            "queryRef": f"{entity}.{prop}", "nativeQueryRef": prop, "active": True}


def visual(name, vtype, x, y, w, h, roles=None, objects=None, z=0, tab=0, sort=None):
    v = {"visualType": vtype}
    if roles:
        v["query"] = {"queryState": {r: {"projections": p} for r, p in roles.items()}}
        v["query"]["sortDefinition"] = sort if sort else {"isDefaultSort": True}
    if objects:
        v["objects"] = objects
    # guide 24a / validate_pbip DRILL_ON_TABLEEX: drillFilterOtherVisuals is invalid on visual
    # types that cannot drill. Emitting it unconditionally was a generator defect - caught by the
    # engine's own linter on the S2 probe report before it reached a delivered page (2026-09-07).
    if vtype not in NO_DRILL:
        v["drillFilterOtherVisuals"] = True
    return {"$schema": S_VIS, "name": name,
            "position": {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": tab},
            "visual": v}


def textbox(name, x, y, w, h, runs, align="Left", z=0, tab=0):
    """runs = [(text, {fontSize, color, bold, italic}), ...]"""
    tr = []
    for text, style in runs:
        st = {}
        if "fontSize" in style: st["fontSize"] = style["fontSize"]
        if "color" in style:    st["color"] = style["color"]
        if style.get("bold"):   st["bold"] = True
        if style.get("italic"): st["italic"] = True
        if "fontFamily" in style: st["fontFamily"] = style["fontFamily"]
        tr.append({"value": text, "textStyle": st})
    objects = {"general": [{"properties": {
        "paragraphs": [{"textRuns": tr, "horizontalTextAlignment": align}]}}]}
    return visual(name, "textbox", x, y, w, h, objects=objects, z=z, tab=tab)


def page(name, display, visuals, width=1280, height=720):
    return {"$schema": S_PAGE, "name": name, "displayName": display,
            "displayOption": "FitToPage", "height": height, "width": width}, visuals


def write(root, pages, model_id, workspace_name, model_name, theme=None, page_order=None):
    """pages = [ (page_dict, [visual_dict, ...]), ... ]"""
    d = os.path.join(root, "definition")
    os.makedirs(d, exist_ok=True)
    conn = (f"Data Source=powerbi://api.powerbi.com/v1.0/myorg/{workspace_name};"
            f"initial catalog={model_name};access mode=readonly;"
            f"integrated security=ClaimsToken;semanticmodelid={model_id}")
    _j(os.path.join(root, "definition.pbir"),
       {"$schema": S_PBIR, "version": "4.0",
        "datasetReference": {"byConnection": {"connectionString": conn}}})
    _j(os.path.join(d, "version.json"), {"$schema": S_VER, "version": "2.0.0"})

    report = {"$schema": S_RPT,
              "themeCollection": {"baseTheme": {"name": "Fluent2-CY26SU07",
                                                "reportVersionAtImport": {"visual": "2.12.0",
                                                                          "report": "3.4.0",
                                                                          "page": "2.3.1"},
                                                "type": "SharedResources"}},
              "resourcePackages": [{"name": "SharedResources", "type": "SharedResources",
                                    "items": [{"name": "Fluent2-CY26SU07",
                                               "path": "BaseThemes/Fluent2-CY26SU07.json",
                                               "type": "BaseTheme"}]}],
              "settings": {"useStylableVisualContainerHeader": True,
                           "exportDataMode": "AllowSummarized",
                           "defaultDrillFilterOtherVisuals": True,
                           "allowChangeFilterTypes": True,
                           "useEnhancedTooltips": True,
                           "useDefaultAggregateDisplayName": True}}
    if theme:
        # shape copied verbatim from Projects/16) Credit Risk Analytics (delivered, renders):
        # customTheme REPLACES baseTheme, and name == path.
        report["themeCollection"] = {"customTheme": {
            "name": theme["name"],
            "reportVersionAtImport": {"visual": "2.12.0", "report": "3.4.0", "page": "2.3.1"},
            "type": "RegisteredResources"}}
        report["resourcePackages"] = [
            {"name": "RegisteredResources", "type": "RegisteredResources",
             "items": [{"name": theme["name"], "path": theme["name"], "type": "CustomTheme"}]}]
        tp = os.path.join(root, "StaticResources", "RegisteredResources")
        os.makedirs(tp, exist_ok=True)
        with open(os.path.join(tp, theme["name"]), "w", encoding="utf-8") as f:
            f.write(theme["json"])
    _j(os.path.join(d, "report.json"), report)

    order = page_order or [p["name"] for p, _ in pages]
    _j(os.path.join(d, "pages", "pages.json"),
       {"$schema": S_PAGES, "pageOrder": order,
        "activePageName": order[0], "landingPageName": order[0]})
    for pg, vis in pages:
        pd = os.path.join(d, "pages", pg["name"])
        _j(os.path.join(pd, "page.json"), pg)
        for v in vis:
            _j(os.path.join(pd, "visuals", v["name"], "visual.json"), v)
    n = sum(len(f) for _, _, f in os.walk(root))
    return n


def _j(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=2)
        f.write("\n")
    with open(path, "r", encoding="utf-8") as f:   # every JSON validated on write
        json.load(f)


COMPONENTS = os.path.join(os.path.expanduser("~"), "mnt", "Power BI Automation Engine",
                          "_ENGINE", "templates", "components")


def from_component(filename, name, x, y, w, h, subs=None, tab=None, z=None):
    """Load a component from _ENGINE/templates/components and substitute its {{PLACEHOLDERS}}.
    The component library is pinned at visualContainer 2.10.0; this project is pinned at 2.11.0
    (P26's version, the one this tenant accepted on 2026-09-06), so the schema is re-stamped."""
    with open(os.path.join(COMPONENTS, filename), encoding="utf-8") as f:
        raw = f.read()
    subs = dict(subs or {})
    subs["VISUAL_NAME"] = name
    for k, v in subs.items():
        raw = raw.replace("{{" + k + "}}", v)
    left = re.findall(r"\{\{([A-Z_]+)\}\}", raw)
    if left:
        raise ValueError(f"{filename}: unsubstituted placeholders {sorted(set(left))}")
    d = json.loads(raw)
    d["$schema"] = S_VIS
    d["position"].update({"x": x, "y": y, "height": h, "width": w})
    if tab is not None:
        d["position"]["tabOrder"] = tab
    if z is not None:
        d["position"]["z"] = z
    return d
