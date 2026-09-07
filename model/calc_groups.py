#!/usr/bin/env python3
"""P27 S3 - the three calculation groups deferred from S2 (kickoff deliverable 3).

SHAPE SOURCE (standing rule: never write TMDL from memory - grep a delivered sibling):
  Projects/24) Fabric E2E FP&A Close & Consolidation (GlobalEnergy)/08_Export/
    SM_FPNA_Consolidation_TMDL/tables/Scenario Calculation Group.tmdl   (and Time ...)
  Read 2026-09-07. That shape is: `table '<Name>'` + lineageTag, a `calculationGroup` block with an
  explicit `precedence:`, N `calculationItem` blocks, then TWO columns (the Name-sourced string
  sorted by Ordinal, and Ordinal itself). **No partition block** - a calculation group has no source.
  No `sourceLineageTag` either: these tables are not bound to the Warehouse.
  `formatStringDefinition` is deliberately NOT used - no delivered sibling in this corpus carries it,
  so writing it would be writing a shape from memory.

PRECEDENCE, and why this order (Microsoft: the HIGHER precedence group is applied on the OUTSIDE,
its SELECTEDMEASURE() expanding to include the lower-precedence group's item):
  10 Attribution Bucket - innermost: pick which bucket of the measure we are looking at
  20 Time              - then apply the day window to that
  30 Currency          - outermost: convert the finished number
Set explicitly on all three, per the kickoff.

TIME INTELLIGENCE IS ON `day_index`, NEVER DAX TIME INTELLIGENCE.
`ref.calendar` is 120 **non-contiguous** business days (Mon-Fri, no holiday table). DATESYTD,
DATEADD, PREVIOUSDAY and friends assume a contiguous date column and would return quietly wrong
numbers here - the failure mode that has no error message. Every item below shifts `day_index`,
which is a dense 1..120 integer sequence over exactly the days that exist.
"""

# ref.bucket, read from the live Warehouse 2026-09-07 (SELECT ... ORDER BY bucket_sort).
# b3 = FX and b4 = Time per the delivered procedure `03_usp_run_eod.sql`, which is the reverse of
# the terminology sheet's prose - the artefact wins (F-21, spec-reconciliation gate).
BUCKETS = [
    (1, "New trades"),
    (2, "Price"),
    (3, "FX"),
    (4, "Time"),
    (5, "Amendments and cancellations"),
    (6, "Unexplained"),
]


def _q(name):
    """TMDL object reference: quote only when the name needs it."""
    return name if name.replace("_", "").isalnum() else f"'{name}'"


def _item(name, dax):
    dax = dax.strip("\n")
    if "\n" not in dax:
        return f"\t\tcalculationItem {_q(name)} = {dax.strip()}"
    body = "\n".join("\t\t\t\t" + ln if ln.strip() else "" for ln in dax.split("\n"))
    return f"\t\tcalculationItem {_q(name)} =\n{body}"


def _cols(display, tag):
    return (
        f"\tcolumn {_q(display)}\n"
        f"\t\tdataType: string\n"
        f"\t\tlineageTag: {tag(display, 'col', 'name')}\n"
        f"\t\tsummarizeBy: none\n"
        f"\t\tsourceColumn: Name\n"
        f"\t\tsortByColumn: Ordinal\n\n"
        f"\t\tannotation SummarizationSetBy = Automatic\n\n"
        f"\tcolumn Ordinal\n"
        f"\t\tdataType: int64\n"
        f"\t\tformatString: 0\n"
        f"\t\tisHidden\n"
        f"\t\tlineageTag: {tag(display, 'col', 'ordinal')}\n"
        f"\t\tsummarizeBy: sum\n"
        f"\t\tsourceColumn: Ordinal\n\n"
        f"\t\tannotation SummarizationSetBy = Automatic\n"
    )


def _table(table_name, column_name, precedence, items, tag):
    L = [f"table {_q(table_name)}", f"\tlineageTag: {tag(table_name)}", "",
         "\tcalculationGroup", f"\t\tprecedence: {precedence}", ""]
    for nm, dax in items:
        L.append(_item(nm, dax))
        L.append("")
    L.append(_cols(column_name, tag))
    return "\n".join(L)


def build_calc_groups(tag):
    """Returns the list build_tmdl.build() takes as calc_groups=[{name, tmdl}, ...]."""

    # ---- 1. Attribution Bucket (precedence 10) -------------------------------------------------
    bucket_items = [
        (name,
         "CALCULATE (\n"
         "    SELECTEDMEASURE (),\n"
         "    REMOVEFILTERS ( 'Bucket' ),\n"
         f"    'Bucket'[bucket_no] = {no}\n"
         ")")
        for no, name in BUCKETS
    ]

    # ---- 2. Time Intelligence (precedence 20), all on day_index ---------------------------------
    time_items = [
        ("Actual", "SELECTEDMEASURE ()"),

        ("Prior Day",
         "VAR d = MAX ( 'Calendar'[day_index] )\n"
         "RETURN\n"
         "CALCULATE (\n"
         "    SELECTEDMEASURE (),\n"
         "    REMOVEFILTERS ( 'Calendar' ),\n"
         "    'Calendar'[day_index] = d - 1\n"
         ")"),

        # 'Current Day' pins the measure to day d. It exists so that 'Day over Day' has a
        # self-consistent left-hand side: without it, SELECTEDMEASURE() at a grand total is the
        # whole context (all 120 days) and differencing that against ONE prior day is meaningless.
        # Caught 2026-09-07 by computing the Warehouse truth before reading the render, not after.
        ("Current Day",
         "VAR d = MAX ( 'Calendar'[day_index] )\n"
         "RETURN\n"
         "CALCULATE (\n"
         "    SELECTEDMEASURE (),\n"
         "    REMOVEFILTERS ( 'Calendar' ),\n"
         "    'Calendar'[day_index] = d\n"
         ")"),

        ("Day over Day",
         "VAR d = MAX ( 'Calendar'[day_index] )\n"
         "VAR _now =\n"
         "    CALCULATE (\n"
         "        SELECTEDMEASURE (),\n"
         "        REMOVEFILTERS ( 'Calendar' ),\n"
         "        'Calendar'[day_index] = d\n"
         "    )\n"
         "VAR _prior =\n"
         "    CALCULATE (\n"
         "        SELECTEDMEASURE (),\n"
         "        REMOVEFILTERS ( 'Calendar' ),\n"
         "        'Calendar'[day_index] = d - 1\n"
         "    )\n"
         "RETURN\n"
         "IF ( NOT ISBLANK ( _prior ), _now - _prior )"),

        ("Month to Date",
         "VAR d = MAX ( 'Calendar'[day_index] )\n"
         "VAR mk =\n"
         "    CALCULATE (\n"
         "        SELECTEDVALUE ( 'Calendar'[month_key] ),\n"
         "        REMOVEFILTERS ( 'Calendar' ),\n"
         "        'Calendar'[day_index] = d\n"
         "    )\n"
         "RETURN\n"
         "CALCULATE (\n"
         "    SELECTEDMEASURE (),\n"
         "    REMOVEFILTERS ( 'Calendar' ),\n"
         "    FILTER (\n"
         "        ALL ( 'Calendar' ),\n"
         "        'Calendar'[month_key] = mk && 'Calendar'[day_index] <= d\n"
         "    )\n"
         ")"),

        ("Rolling 5 Business Days",
         "VAR d = MAX ( 'Calendar'[day_index] )\n"
         "RETURN\n"
         "CALCULATE (\n"
         "    SELECTEDMEASURE (),\n"
         "    REMOVEFILTERS ( 'Calendar' ),\n"
         "    FILTER (\n"
         "        ALL ( 'Calendar' ),\n"
         "        'Calendar'[day_index] > d - 5 && 'Calendar'[day_index] <= d\n"
         "    )\n"
         ")"),

        ("Rolling 20 Business Days",
         "VAR d = MAX ( 'Calendar'[day_index] )\n"
         "RETURN\n"
         "CALCULATE (\n"
         "    SELECTEDMEASURE (),\n"
         "    REMOVEFILTERS ( 'Calendar' ),\n"
         "    FILTER (\n"
         "        ALL ( 'Calendar' ),\n"
         "        'Calendar'[day_index] > d - 20 && 'Calendar'[day_index] <= d\n"
         "    )\n"
         ")"),
    ]

    # ---- 3. Currency (precedence 30) -------------------------------------------------------------
    # Guarded by measure name. A calculation group applies to EVERY measure, and dividing a lot
    # count, a percentage or a tonnage by an FX rate is nonsense - so only measures whose name
    # carries the "(MYR)" unit tag are converted; everything else passes through untouched. The
    # rate is [USDMYR Rate] = the rate at the latest day_index in context (see 'FX Rate'.tmdl),
    # so a multi-day total is converted at the last day's rate. Stated, not hidden.
    currency_items = [
        ("MYR", "SELECTEDMEASURE ()"),
        ("USD",
         "VAR _isMYR = CONTAINSSTRING ( SELECTEDMEASURENAME (), \"(MYR)\" )\n"
         "VAR _rate = [USDMYR Rate]\n"
         "RETURN\n"
         "IF (\n"
         "    _isMYR && NOT ISBLANK ( _rate ),\n"
         "    DIVIDE ( SELECTEDMEASURE (), _rate ),\n"
         "    SELECTEDMEASURE ()\n"
         ")"),
    ]

    return [
        {"name": "Attribution Bucket Calculation Group",
         "tmdl": _table("Attribution Bucket Calculation Group", "Attribution Bucket", 10,
                        bucket_items, tag)},
        {"name": "Time Calculation Group",
         "tmdl": _table("Time Calculation Group", "Time Intelligence", 20, time_items, tag)},
        {"name": "Currency Calculation Group",
         "tmdl": _table("Currency Calculation Group", "Currency", 30, currency_items, tag)},
    ]
