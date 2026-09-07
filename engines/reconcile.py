#!/usr/bin/env python3
"""Reconcile Fabric warehouse engine aggregates (wh_Q*.csv) against expected_aggregates.json."""
import csv
import json
from decimal import Decimal
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"

SPECS = [
    # (query label, expected list key, csv file, key field, field -> kind)
    ("Q1", "attribution_daily", "wh_Q1.csv", ("biz_date",),
     {"biz_date": "date", "mtm_open": "dec", "mtm_close": "dec", "d_mtm": "dec",
      "b1": "dec", "b2": "dec", "b3": "dec", "b4": "dec", "b5": "dec", "b6": "dec",
      "realised": "dec", "restated": "int"}),
    ("Q2", "mtm_daily_by_day", "wh_Q2.csv", ("biz_date",),
     {"biz_date": "date", "n": "int", "sum_mtm": "dec", "sum_abs": "dec", "sum_qty": "dec"}),
    ("Q3", "exposure_by_day", "wh_Q3.csv", ("biz_date",),
     {"biz_date": "date", "sum_exposure": "dec", "sum_ecl": "dec", "n_breach": "int"}),
    ("Q4", "exposure_by_cp", "wh_Q4.csv", ("cp_id",),
     {"cp_id": "int", "sum_exposure": "dec", "sum_util": "dec", "n_breach": "int", "first_breach": "datestr"}),
]


def norm(kind, v):
    if v is None:
        v = ""
    v = str(v).strip()
    if kind == "dec":
        return Decimal(v) if v != "" else None
    if kind == "int":
        return int(Decimal(v)) if v != "" else None
    if kind in ("date", "datestr"):
        return v[:10] if v else ""
    return v


def main():
    expected = json.loads((OUT / "expected_aggregates.json").read_text())
    total = 0
    for label, key, fname, keyf, fields in SPECS:
        exp_rows = expected[key]
        with open(OUT / fname, newline="") as fh:
            act_rows = list(csv.DictReader(fh))
        print(f"== {label} ({key} vs {fname}) ==")
        print(f"  expected rows: {len(exp_rows)}  actual rows: {len(act_rows)}")
        mism = []
        rows_compared = 0
        n = min(len(exp_rows), len(act_rows))
        if len(exp_rows) != len(act_rows):
            mism.append(("<rowcount>", "rows", len(exp_rows), len(act_rows)))
        for i in range(n):
            e, a = exp_rows[i], act_rows[i]
            rows_compared += 1
            k = "|".join(str(norm(fields[f], e.get(f))) for f in keyf)
            row_bad = False
            for f, kind in fields.items():
                ev, av = norm(kind, e.get(f)), norm(kind, a.get(f))
                if ev != av:
                    row_bad = True
                    mism.append((k, f, e.get(f), a.get(f)))
        bad_rows = len({m[0] for m in mism})
        total += rows_compared
        print(f"  rows compared: {rows_compared}  mismatching rows: {bad_rows}  mismatching fields: {len(mism)}")
        for m in mism[:5]:
            print(f"    key={m[0]} field={m[1]} expected={m[2]!r} actual={m[3]!r}")
    print(f"TOTAL rows compared across all four: {total}")


if __name__ == "__main__":
    main()
