#!/usr/bin/env python3
"""P27 S2 - generate SM_PalmDesk TMDL (Direct Lake over WH_PalmDesk).
Schema shapes copied from the S1 gate probe (00_Plan/gate_probe/SM_Gate_Probe.SemanticModel),
which the tenant accepted 2026-09-06. CRLF on every .tmdl (CORE_RULES).
Column list is generated from the INFORMATION_SCHEMA read of the live Warehouse, not from memory.
"""
import json, os, sys, uuid

WS  = "b06ab341-0860-4341-a6c9-5986d0d7f4b0"
WH  = "43516adb-2f22-46e6-8fa4-3ad499483171"
NS  = uuid.UUID("27000000-0000-0000-0000-000000000027")   # stable lineageTags across re-runs
EXPR = "DirectLake - WH_PalmDesk"
# PROVEN 2026-09-07 (F-29): this Warehouse binds through **Direct Lake on SQL**, not Direct Lake on
# OneLake. The AzureStorage.DataLake (OneLake) form validates on create and then never loads its
# tables - every visual returns Missing_References. Sql.Database against the SQL analytics endpoint
# renders correctly and returns the Warehouse's own numbers. Attribution is clean: the bare
# sourceLineageTag fix and the dropped HierarchicalNavigation option were each pushed, refreshed and
# rendered on their own and BOTH still failed; only the connector swap moved it.
SQL_ENDPOINT = "<SQL-ENDPOINT>.datawarehouse.fabric.microsoft.com"

def tag(*parts):
    return str(uuid.uuid5(NS, "|".join(parts)))

# (friendly name, schema, entity, [ (col, tsql_type, prec, scale) ... ])  -- from INFORMATION_SCHEMA
TABLES = json.load(open(os.path.join(os.path.dirname(__file__), "columns.json")))

# T-SQL -> TMDL dataType + default formatString
def map_type(t, prec, scale):
    t = t.lower()
    if t in ("int", "bigint", "smallint", "tinyint"):
        return "int64", "0"
    if t in ("decimal", "numeric", "money"):
        return "decimal", "#,##0.00" if int(scale or 0) <= 2 else "#,##0.0000"
    if t in ("float", "real"):
        return "double", None
    if t == "bit":
        return "boolean", None
    if t == "date":
        return "dateTime", "yyyy-mm-dd"
    if t.startswith("datetime"):
        return "dateTime", "yyyy-mm-dd hh:nn:ss"
    return "string", None

# columns that must never be implicitly summed
NO_SUM = {"cp_id", "id", "hedge_rel_id", "contract_id", "s", "version_no", "day_index",
          "tau", "designated_lots", "bucket_no", "bucket_sort", "month_key", "payment_terms_days"}

# column -> the column it sorts by (both must live in the same table)
SORT_BY = {("Bucket", "bucket_name"): "bucket_sort", ("Bucket", "bucket_code"): "bucket_sort"}
# columns hidden from the report field list
HIDDEN = {("Bucket", "bucket_sort"), ("Attribution Bucket Daily", "bucket_no"),
          ("Calendar", "day_index"), ("Attribution Daily", "sum_b"), ("Attribution Daily", "run_ts")}

def col_block(tbl, c):
    name, ttype, prec, scale = c["COLUMN_NAME"], c["DATA_TYPE"], c["NUMERIC_PRECISION"], c["NUMERIC_SCALE"]
    dt, fmt = map_type(ttype, prec, scale)
    summarize = "sum" if (dt in ("int64", "decimal", "double") and name not in NO_SUM) else "none"
    L = [f"\tcolumn {name}", f"\t\tdataType: {dt}"]
    if fmt:
        L.append(f"\t\tformatString: {fmt}")
    if (tbl, name) in HIDDEN:
        L.append("\t\tisHidden")
    L += [f"\t\tlineageTag: {tag(tbl, name)}",
          f"\t\tsourceLineageTag: {name}",
          f"\t\tsummarizeBy: {summarize}",
          f"\t\tsourceColumn: {name}"]
    if (tbl, name) in SORT_BY:
        L.append(f"\t\tsortByColumn: {SORT_BY[(tbl, name)]}")
    if dt == "dateTime":
        L.append("\t\tannotation SummarizationSetBy = Automatic")
    return "\n".join(L)

def table_tmdl(t, measures):
    friendly, schema, entity = t["friendly"], t["schema"], t["entity"]
    # Microsoft Learn, "Lineage tags for Power BI semantic models": for DirectLake models the
    # sourceLineageTag must be the NAME of the table/column in the lakehouse/warehouse. It is NOT
    # the two-part [schema].[table] form, which is what this engine wrote until 2026-09-07 (copied
    # from a Direct Lake on SQL example, where the two-part form is correct). Columns were already
    # bare names and are unchanged. Verified against the doc, not against a render - see F-25.
    L = [f"table '{friendly}'", f"\tlineageTag: {tag(friendly)}",
         f"\tsourceLineageTag: {entity}", ""]
    for m in measures.get(friendly, []):
        L.append(m.rstrip())
        L.append("")
    for c in t["columns"]:
        L.append(col_block(friendly, c))
        L.append("")
    L += [f"\tpartition '{friendly}' = entity",
          "\t\tmode: directLake",
          "\t\tsource",
          f"\t\t\tentityName: {entity}",
          f"\t\t\tschemaName: {schema}",
          f"\t\t\texpressionSource: '{EXPR}'", ""]
    return "\n".join(L)

def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="\r\n", encoding="utf-8") as f:
        f.write(text)

def build(outdir, measures=None, relationships=True, calc_groups=None):
    measures = measures or {}
    d = os.path.join(outdir, "SM_PalmDesk.SemanticModel")
    defn = os.path.join(d, "definition")
    write(os.path.join(d, "definition.pbism"), json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "5.0", "settings": {"qnaEnabled": False}}, indent=2) + "\n")
    write(os.path.join(defn, "database.tmdl"), "database SM_PalmDesk\n\tcompatibilityLevel: 1702\n")
    write(os.path.join(defn, "expressions.tmdl"),
          f"expression '{EXPR}' =\n"
          f"\t\tlet\n"
          f'\t\t    Source = Sql.Database("{SQL_ENDPOINT}", "{WH}")\n'
          f"\t\tin\n"
          f"\t\t    Source\n"
          f"\tlineageTag: {tag('expr')}\n\n"
          f"\tannotation PBI_IncludeFutureArtifacts = False\n")

    names = [t["friendly"] for t in TABLES] + [c["name"] for c in (calc_groups or [])]
    model = ["model Model", "\tculture: en-US",
             "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
             "\tdiscourageImplicitMeasures", "\tsourceQueryCulture: en-US",
             "\tdataAccessOptions", "\t\tlegacyRedirects", "\t\treturnErrorValuesAsNull", "",
             f'annotation PBI_QueryOrder = ["{EXPR}"]', "",
             'annotation PBI_ProTooling = ["DirectLakeOnOneLakeInWeb"]', ""]
    for n in names:
        model.append(f"ref table '{n}'")
    model.append("")
    write(os.path.join(defn, "model.tmdl"), "\n".join(model))

    for t in TABLES:
        write(os.path.join(defn, "tables", f"{t['friendly']}.tmdl"), table_tmdl(t, measures))
    for cg in (calc_groups or []):
        write(os.path.join(defn, "tables", f"{cg['name']}.tmdl"), cg["tmdl"])

    if relationships:
        rels = []
        for (ft, fc, tt, tc, extra) in RELS:
            rid = tag("rel", ft, fc, tt, tc)
            block = [f"relationship {rid}",
                     f"\tfromColumn: '{ft}'.{fc}",
                     f"\ttoColumn: '{tt}'.{tc}"]
            block += extra
            rels.append("\n".join(block))
        write(os.path.join(defn, "relationships.tmdl"), "\n\n".join(rels) + "\n")
    return d

RELS = [
    ("MTM Daily",          "biz_date",     "Calendar",           "biz_date",     []),
    ("Attribution Daily",  "biz_date",     "Calendar",           "biz_date",     []),
    ("Exposure Daily",     "biz_date",     "Calendar",           "biz_date",     []),
    ("Exposure Daily",     "cp_id",        "Counterparty",       "cp_id",        []),
    ("MTM Daily",          "cp_id",        "Counterparty",       "cp_id",        []),
    ("MTM Daily",          "product_code", "Product",            "product_code", []),
    ("Physical Contract",  "cp_id",        "Counterparty",       "cp_id",        []),
    ("Physical Contract",  "product_code", "Product",            "product_code", []),
    ("Hedge Test Monthly", "hedge_rel_id", "Hedge Relationship", "hedge_rel_id", []),
    ("Hedge Relationship", "product_code", "Product",            "product_code", ["\tisActive: false"]),
    ("Attribution Bucket Daily", "biz_date",  "Calendar", "biz_date",  []),
    ("Attribution Bucket Daily", "bucket_no", "Bucket",   "bucket_no", []),
    ("FX Rate",                  "rate_date", "Calendar", "biz_date",  []),
]

if __name__ == "__main__":
    import measures as _m, calc_groups as _cg, alt_text as _at
    _M = _m.build_measures(tag)
    # S3: the 32 altText narration measures ride on the same tables as the visuals they describe.
    for _t, _blocks in _at.build_alt_measures(tag).items():
        _M.setdefault(_t, []).extend(_blocks)
    out = build(os.path.dirname(os.path.abspath(__file__)), measures=_M,
                calc_groups=_cg.build_calc_groups(tag))
    n = sum(len(files) for _, _, files in os.walk(out))
    print(f"wrote {n} files under {out}")
    print(f"tables: {len(TABLES)}  columns: {sum(len(t['columns']) for t in TABLES)}  "
          f"relationships: {len(RELS)}  measures: {len(_m.M)}")
