#!/usr/bin/env python3
"""
P27 PalmDesk — offline replay of the Warehouse engines (P24 rule: same formulas, second implementation).
Reads 01_Source/out/data/*.csv, runs all 120 business days, writes 03_Engines/out/*.csv.
Every number is Decimal, rounded ROUND_HALF_UP at exactly the points the T-SQL rounds (ROUND(x,n)).

Formulas (METHODOLOGY_NOTES.md, order new -> curve -> FX -> time -> actualisation; bucket 6 = plug):
  P(prod, d, tau)   curve interpolated linearly on tenor days between points at the 15th of each listed month,
                    flat beyond both ends, rounded to 4 dp; latest version with published_at <= as_of
  MTM(t,d)          R2( s * Q * (P - K) * FX )           s=+1 buy / -1 sell; FX = MYR per price ccy, 1 for MYR
  B2 curve          R2( s*Q0*(P(tau0,d)   - P(tau0,d-1)) * F0 )
  B3 fx             R2( s*Q0*(P(tau0,d)   - K0)          * (F1-F0) )
  B4 time           R2( s*Q0*(P(tau1,d)   - P(tau0,d))   * F1 )      (0 for futures: fixed tenor)
  B5 actualisation  MTM1 - MTM0 - B2 - B3 - B4  for positions whose version/open qty changed on d (else 0)
  B1 new deals      R2( s*Q*(P(tau,d) - K_confirmed) * F1 )  for trades dated d  -> MTM1 uses BOOKED K
  B6 unexplained    dMTM_total - (B1+..+B5)                 (rounding cents + any booking error)
Exposure(c,d) = max(0, MTM_net) [netting] or sum(max(0,MTM)) + AR_open + Unbilled + DeliveryRisk - Collateral(haircut)
"""
import csv, json, os, sys
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP, getcontext
getcontext().prec = 38
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "01_Source", "out", "data")
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
D = Decimal
def R(x, n=2): return D(x).quantize(D(1).scaleb(-n), rounding=ROUND_HALF_UP)
def dt(s): return date.fromisoformat(s)
def load(t): return list(csv.DictReader(open(os.path.join(DATA, t + ".csv"))))
LOT = 25
AMBER, RED = D("0.75"), D("0.90"); DR_WINDOW = 30; LC_HAIRCUT = D("0.10")
BAND_LO, BAND_HI = D("0.80"), D("1.25")

cal = [dt(r["biz_date"]) for r in load("ref.calendar")]
month_end = {dt(r["biz_date"]) for r in load("ref.calendar") if r["is_month_end"] == "1"}
cps = {int(r["cp_id"]): r for r in load("ref.counterparty")}
limits = {int(r["cp_id"]): D(r["approved_limit_myr"]) for r in load("ref.credit_limit")}
coll = defaultdict(D)
for r in load("ref.collateral"):
    h = LC_HAIRCUT if r["collateral_type"] == "LC" else D(0)
    coll[int(r["cp_id"])] += R(D(r["amount_myr"]) * (1 - h))
ecl = {(r["grade"], r["ageing_band"]): D(r["rate"]) for r in load("ref.ecl_rate")}
contracts = {int(r["contract_id"]): r for r in load("trd.physical_contract")}
versions = defaultdict(list)
for r in load("trd.contract_version"): versions[int(r["contract_id"])].append((dt(r["valid_from"]), int(r["version_no"]), D(r["quantity_mt"]), D(r["price"]), r["status"]))
for v in versions.values(): v.sort()
futs = load("trd.futures_trade")
hedges = {int(r["hedge_rel_id"]): r for r in load("trd.hedge_relationship")}
actuals = load("ops.actualisation")
invoices = load("ops.invoice"); payments = load("ops.payment")
curve_rows = load("mkt.curve"); fx_rows = load("mkt.fx_rate"); hist = load("mkt.monthly_history")

# curve store: (prod, curve_date) -> list of (published_at, version, {tenor_month: price})
CV = defaultdict(dict)
for r in curve_rows:
    CV[(r["product_code"], dt(r["curve_date"]))].setdefault((dt(r["published_at"]), int(r["version"])), {})[r["tenor_month"]] = D(r["price"])
FXR = {(r["ccy_pair"], dt(r["rate_date"])): D(r["rate"]) for r in fx_rows}
def fx(ccy, d):
    if ccy == "MYR": return D("1.000000")
    return FXR[(ccy + "MYR", d)]
def m15(tm): y, m = map(int, tm.split("-")); return date(y, m, 15)
def curve_points(prod, d, as_of):
    vers = [k for k in CV[(prod, d)] if k[0] <= as_of]
    k = max(vers)                                   # latest published version known at as_of
    pts = sorted(((m15(tm) - d).days, px) for tm, px in CV[(prod, d)][k].items())
    return pts
def P(prod, d, tau, as_of):
    pts = curve_points(prod, d, as_of)
    if tau <= pts[0][0]: return R(pts[0][1], 4)
    if tau >= pts[-1][0]: return R(pts[-1][1], 4)
    for (t0, p0), (t1, p1) in zip(pts, pts[1:]):
        if t0 <= tau <= t1:
            return R((p0 * (t1 - tau) + p1 * (tau - t0)) / D(t1 - t0), 4)
def settle(tm, d, as_of): return R(dict((k, v) for k, v in CV[("CPO", d)][max(k for k in CV[("CPO", d)] if k[0] <= as_of)].items())[tm], 4)

def version_asof(cid, d):
    cur = None
    for (vf, vn, qty, px, st) in versions[cid]:
        if vf <= d: cur = (vn, qty, px, st)
    return cur
act_by_c = defaultdict(list)
for a in actuals: act_by_c[int(a["contract_id"])].append(a)
def actualised_qty(cid, d):   # as seen by the engine at run date d: recorded_date <= d
    return sum((D(a["quantity_mt"]) for a in act_by_c[cid] if dt(a["recorded_date"]) <= d), D(0))

def positions(d, as_of):
    """Open positions valued at d. Returns dict key -> (s, Q, P, K, F, prod, cp, tau, kind, version_key)."""
    pos = {}
    for cid, c in contracts.items():
        if dt(c["trade_date"]) > d: continue
        v = version_asof(cid, d)
        if v is None or v[3] != "OPEN": continue
        qopen = v[1] - actualised_qty(cid, d)
        if qopen <= 0: continue
        s = 1 if c["side"] == "B" else -1
        tau = (dt(c["delivery_date"]) - d).days
        px = P(c["product_code"], d, tau, as_of)
        pos[("P", cid)] = dict(s=s, Q=qopen, P=px, K=v[2], F=fx(c["price_ccy"], d), prod=c["product_code"], cp=int(c["cp_id"]),
                               tau=tau, kind="P", vkey=(v[0], qopen), ccy=c["price_ccy"], ref=c["contract_ref"], tenor=None)
    for f in futs:
        td = dt(f["trade_date"]); cd = dt(f["close_date"]) if f["close_date"] else None
        if td > d or (cd is not None and cd <= d): continue
        s = 1 if f["side"] == "B" else -1
        pos[("F", int(f["trade_id"]))] = dict(s=s, Q=D(int(f["lots"]) * LOT), P=settle(f["contract_month"], d, as_of), K=D(f["price_myr"]), F=D("1.000000"),
                                             prod="CPO", cp=None, tau=None, kind="F", vkey=(1, D(int(f["lots"]) * LOT)), ccy="MYR", ref=f["trade_ref"], tenor=f["contract_month"])
    return pos
def mtm(p): return R(D(p["s"]) * p["Q"] * (p["P"] - p["K"]) * p["F"])

# ---------------------------------------------------------------- daily run
mtm_rows, attr_rows, attr_trade, expo_rows, ctl_rows = [], [], [], [], []
prev = {}; prev_date = None
inv_by_id = {int(i["invoice_id"]): i for i in invoices}
pay_by_inv = defaultdict(list)
for p in payments: pay_by_inv[int(p["invoice_id"])].append(p)
conf_price = {cid: D(c["confirmed_price"]) for cid, c in contracts.items()}
def run_day(d, as_of, restated=0):
    global prev, prev_date
    cur = positions(d, as_of)
    for k, p in cur.items(): p["mtm"] = mtm(p)
    # ---- attribution
    b = defaultdict(D); realised = D(0)
    for k, p in cur.items():
        row = dict(biz_date=d.isoformat(), ref=p["ref"], kind=p["kind"], b1=D(0), b2=D(0), b3=D(0), b4=D(0), b5=D(0), b6=D(0), mtm_open=D(0), mtm_close=p["mtm"])
        if k in prev:
            q0 = prev[k]
            row["mtm_open"] = q0["mtm"]
            if p["kind"] == "P":
                P_old_new = P(p["prod"], d, q0["tau"], as_of)      # today's curve at yesterday's tenor
                row["b2"] = R(D(q0["s"]) * q0["Q"] * (P_old_new - q0["P"]) * q0["F"])
                row["b3"] = R(D(q0["s"]) * q0["Q"] * (P_old_new - q0["K"]) * (p["F"] - q0["F"]))
                row["b4"] = R(D(q0["s"]) * q0["Q"] * (p["P"] - P_old_new) * p["F"])
            else:
                row["b2"] = R(D(q0["s"]) * q0["Q"] * (p["P"] - q0["P"]) * q0["F"])
            resid = p["mtm"] - q0["mtm"] - row["b2"] - row["b3"] - row["b4"]
            if p["vkey"] != q0["vkey"]: row["b5"] = resid
            else: row["b6"] = resid
        else:
            # new deal (trade_date == d) or a late-recorded reopen; value at CONFIRMED price for bucket 1
            kc = conf_price[k[1]] if p["kind"] == "P" else p["K"]
            row["b1"] = R(D(p["s"]) * p["Q"] * (p["P"] - kc) * p["F"])
            row["b6"] = p["mtm"] - row["b1"]
        attr_trade.append(row)
        for kk in ("b1", "b2", "b3", "b4", "b5", "b6", "mtm_open", "mtm_close"): b[kk] += row[kk]
    for k, q0 in prev.items():
        if k not in cur:      # left the book: actualised/cancelled/closed -> bucket 5
            row = dict(biz_date=d.isoformat(), ref=q0["ref"], kind=q0["kind"], b1=D(0), b2=D(0), b3=D(0), b4=D(0), b5=-q0["mtm"], b6=D(0), mtm_open=q0["mtm"], mtm_close=D(0))
            attr_trade.append(row); b["b5"] += row["b5"]; b["mtm_open"] += q0["mtm"]
    # realised: actualisations recorded today + futures closed today
    for a in actuals:
        if dt(a["recorded_date"]) == d:
            c = contracts[int(a["contract_id"])]; s = 1 if c["side"] == "B" else -1
            v = version_asof(int(a["contract_id"]), d)
            realised += R(D(s) * D(a["quantity_mt"]) * (D(a["actual_price"]) * (1 + D(a["quality_adj_pct"])) - v[2]) * fx(c["price_ccy"], d))
    for f in futs:
        if f["close_date"] and dt(f["close_date"]) == d:
            s = 1 if f["side"] == "B" else -1
            realised += R(D(s) * D(int(f["lots"]) * LOT) * (D(f["close_price"]) - D(f["price_myr"])))
    dm = b["mtm_close"] - b["mtm_open"]
    attr_rows.append(dict(biz_date=d.isoformat(), mtm_open=b["mtm_open"], mtm_close=b["mtm_close"], d_mtm=dm, b1=b["b1"], b2=b["b2"], b3=b["b3"], b4=b["b4"], b5=b["b5"], b6=b["b6"],
                          sum_b=b["b1"] + b["b2"] + b["b3"] + b["b4"] + b["b5"] + b["b6"], realised=realised, restated=restated))
    for k, p in cur.items():
        mtm_rows.append(dict(biz_date=d.isoformat(), ref=p["ref"], kind=p["kind"], product=p["prod"], cp_id=p["cp"] or "", tenor=p["tenor"] or "", quantity=p["Q"], curve_price=p["P"], contract_price=p["K"], fx=p["F"], mtm_myr=p["mtm"]))
    # ---- exposure
    for cid, c in cps.items():
        mt = [p["mtm"] for p in cur.values() if p["cp"] == cid]
        mtm_net = max(D(0), sum(mt, D(0))) if c["has_netting"] == "1" else sum((max(D(0), x) for x in mt), D(0))
        ar = D(0); ecl_amt = D(0); bands = defaultdict(D)
        for inv in invoices:
            if int(inv["cp_id"]) != cid or inv["side"] != "S" or dt(inv["invoice_date"]) > d: continue
            paid = sum((D(p["amount_myr"]) for p in pay_by_inv[int(inv["invoice_id"])] if dt(p["payment_date"]) <= d), D(0))
            openamt = D(inv["amount_myr"]) - paid
            if openamt <= 0: continue
            ar += openamt
            age = (d - dt(inv["due_date"])).days
            band = "0-30" if age <= 30 else "31-60" if age <= 60 else "61-90" if age <= 90 else "90+"
            ecl_amt += R(openamt * ecl[(c["grade"], band)])
        unbilled = D(0)
        for a in actuals:
            ct = contracts[int(a["contract_id"])]
            if int(ct["cp_id"]) != cid or ct["side"] != "S" or dt(a["recorded_date"]) > d: continue
            invd = [i for i in invoices if int(i["contract_id"]) == int(a["contract_id"]) and dt(i["invoice_date"]) <= d]
            if invd: continue
            v = version_asof(int(a["contract_id"]), d)
            unbilled += R(D(a["quantity_mt"]) * D(a["actual_price"]) * fx(ct["price_ccy"], d))
        drisk = D(0)
        if c["we_deliver_first"] == "1":
            for k, p in cur.items():
                if p["kind"] == "P" and p["cp"] == cid and p["s"] == -1 and 0 <= p["tau"] <= DR_WINDOW:
                    drisk += R(p["Q"] * p["K"] * p["F"])
        expo = mtm_net + ar + unbilled + drisk - coll[cid]
        util = R(expo / limits[cid], 4)
        band = "GREEN" if util < AMBER else "AMBER" if util < RED else "RED" if util <= 1 else "BREACH"
        expo_rows.append(dict(biz_date=d.isoformat(), cp_id=cid, mtm_net=mtm_net, ar_open=ar, unbilled=unbilled, delivery_risk=drisk, collateral=coll[cid], exposure=expo, limit_myr=limits[cid], utilisation=util, band=band, ecl=ecl_amt))
    prev = cur; prev_date = d

for i, d in enumerate(cal):
    run_day(d, d)
# restatement: CPO curve for day 45 republished on day 48 -> re-run 45..47 with as_of = day 48, then day 48 sees consistent opens
RD = date(2026, 5, 15); RP = date(2026, 5, 20)
ri = cal.index(RD); rp = cal.index(RP)
# re-run from day 45 through the end using the restated curve (day 48+ MTM unchanged, but their opens must match)
prev = {}; prev_date = None
saved = dict(mtm=mtm_rows, attr=attr_rows, at=attr_trade, ex=expo_rows)
mtm_rows, attr_rows, attr_trade, expo_rows = [], [], [], []
for d in cal[:ri]:
    run_day(d, d)
for d in cal[ri:]:
    run_day(d, max(d, RP), restated=1 if ri <= cal.index(d) < rp else 0)
RESTATED_ROWS = dict(mtm=mtm_rows, attr=attr_rows, at=attr_trade, ex=expo_rows)

# ---------------------------------------------------------------- hedge effectiveness (monthly)
hedge_rows = []
def fv_item(h, d, as_of):
    prod, fm = h["product_code"], h["forecast_month"]
    tau = (m15(fm) - d).days
    return R(D(h["forecast_qty_mt"]) * P(prod, d, tau, as_of) * (fx("USD", d) if prod != "CPO" else D(1)))
def closeout_date(fm):       # expiry convention: last business day of the month preceding the contract month
    y, m = map(int, fm.split("-")); pm = f"{y - 1 if m == 1 else y:04d}-{12 if m == 1 else m - 1:02d}"
    c = [d for d in cal if d.isoformat()[:7] == pm]
    return c[-1] if c else None
def fv_instr(h, d, as_of):   # short lots: value = -lots*25*settle; frozen at the close-out price once closed
    co = closeout_date(h["forecast_month"])
    dd = min(d, co) if co else d
    return R(-D(int(h["designated_lots"]) * LOT) * settle(h["forecast_month"], dd, min(as_of, max(dd, RP) if dd >= RD else dd)))
# prospective regression on 24 months of history: dFV_item vs dFV_instr (monthly changes)
H = defaultdict(dict)
for r in hist: H[r["series"]][r["month_key"]] = D(r["price"])
months = sorted(H["CPO"])
oci = defaultdict(D)
for hid, h in hedges.items():
    xs, ys = [], []
    for m0, m1 in zip(months, months[1:]):
        di = -D(int(h["designated_lots"]) * LOT) * (H["CPO"][m1] - H["CPO"][m0])
        if h["product_code"] == "CPO": item = D(h["forecast_qty_mt"]) * (H["CPO"][m1] - H["CPO"][m0])
        else: item = D(h["forecast_qty_mt"]) * (H[h["product_code"]][m1] * H["USDMYR"][m1] - H[h["product_code"]][m0] * H["USDMYR"][m0])
        xs.append(di); ys.append(item)
    n = D(len(xs)); sx = sum(xs); sy = sum(ys); sxx = sum(x * x for x in xs); sxy = sum(x * y for x, y in zip(xs, ys)); syy = sum(y * y for y in ys)
    slope = R((n * sxy - sx * sy) / (n * sxx - sx * sx), 4)
    r2 = R(((n * sxy - sx * sy) ** 2) / ((n * sxx - sx * sx) * (n * syy - sy * sy)), 4)
    prospective = (D("-1.25") <= slope <= D("-0.80")) and r2 >= D("0.80")
    dd = dt(h["designation_date"])
    base_item, base_instr = fv_item(h, dd, dd), fv_instr(h, dd, dd)
    cum_item_prev = cum_instr_prev = D(0); oci_bal = D(0); reclassified = False
    notional = R(D(h["forecast_qty_mt"]) * (P(h["product_code"], dd, (m15(h["forecast_month"]) - dd).days, dd)) * (fx("USD", dd) if h["product_code"] != "CPO" else D(1)))
    floor = R(notional * D("0.01"))                 # de minimis: cumulative item change below 1% of notional is not assessed (S1 amendment)
    co = closeout_date(h["forecast_month"])
    for me in sorted(month_end):
        if me < dd or me.isoformat()[:7] > h["forecast_month"]: continue
        mk = me.isoformat()[:7]
        as_of = max(me, RP) if me >= RD else me
        if mk == h["forecast_month"]:
            # month of sale: the forecast transaction actualises; OCI reclassifies to P&L, no new measurement
            reclass = -oci_bal
            hedge_rows.append(dict(month_key=mk, hedge_rel_id=hid, product=h["product_code"], forecast_month=h["forecast_month"], cum_dfv_item=cum_item_prev, cum_dfv_instr=cum_instr_prev,
                                   dollar_offset="", assessed=0, prospective_slope=slope, prospective_r2=r2, effective=1 if prospective else 0,
                                   ineffectiveness_pl=D(0), oci_open=oci_bal, oci_effective_added=D(0), oci_reclassified=reclass, oci_close=D(0)))
            oci_bal = D(0); continue
        ci = fv_item(h, me, as_of) - base_item; cin = fv_instr(h, me, as_of) - base_instr
        assessed = abs(ci) >= floor
        ratio = R(cin / ci, 4) if assessed else None
        effective = prospective and (not assessed or BAND_LO <= abs(ratio) <= BAND_HI)
        d_instr = cin - cum_instr_prev
        eff_cum = max(-abs(ci), min(abs(ci), cin))               # lower-of: instrument change capped at the item change
        oci_add = (eff_cum - oci_bal) if effective else (D(0) - oci_bal)
        ineff = d_instr - oci_add
        oci_open = oci_bal; oci_bal += oci_add
        hedge_rows.append(dict(month_key=mk, hedge_rel_id=hid, product=h["product_code"], forecast_month=h["forecast_month"], cum_dfv_item=ci, cum_dfv_instr=cin,
                               dollar_offset=ratio if ratio is not None else "", assessed=1 if assessed else 0, prospective_slope=slope, prospective_r2=r2, effective=1 if effective else 0,
                               ineffectiveness_pl=ineff, oci_open=oci_open, oci_effective_added=oci_add, oci_reclassified=D(0), oci_close=oci_bal))
        cum_item_prev, cum_instr_prev = ci, cin

# ---------------------------------------------------------------- write
def w(name, rows):
    if not rows: return
    with open(os.path.join(OUT, name), "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys())); wr.writeheader(); wr.writerows(rows)
w("mtm_daily.csv", mtm_rows); w("attribution_daily.csv", attr_rows); w("attribution_trade.csv", attr_trade); w("exposure_daily.csv", expo_rows); w("hedge_test_monthly.csv", hedge_rows)
# control totals + injected-truth checks
last = cal[-1].isoformat()
pos_last = [r for r in mtm_rows if r["biz_date"] == last]
by_tenor = defaultdict(D)
for r in pos_last:
    key = (r["product"], r["tenor"] or "phys")
    by_tenor[key] += r["quantity"] * (1 if r["mtm_myr"] >= 0 or True else 1)
ctl = {"mtm_total_day120": str(sum(r["mtm_myr"] for r in pos_last)), "n_positions_day120": len(pos_last),
       "sum_buckets_eq_dmtm_all_days": all(a["sum_b"] == a["d_mtm"] for a in attr_rows),
       "max_abs_unexplained_nonengineered": None, "unexplained_engineered": {}, "breaches": [], "hedge_fail_months": []}
eng_days = set()
for r in attr_trade:
    if r["kind"] == "P" and r["ref"] in ("PC00102", "PC00270", "PC00430") and r["b6"] != 0:
        ctl["unexplained_engineered"][r["ref"]] = (r["biz_date"], str(r["b6"])); eng_days.add(r["biz_date"])
ctl["max_abs_unexplained_nonengineered"] = str(max(abs(a["b6"]) for a in attr_rows if a["biz_date"] not in eng_days))
ctl["unexplained_on_engineered_days"] = {a["biz_date"]: str(a["b6"]) for a in attr_rows if a["biz_date"] in eng_days}
seen = set()
for r in expo_rows:
    if r["band"] == "BREACH" and r["cp_id"] not in seen:
        seen.add(r["cp_id"]); ctl["breaches"].append((r["cp_id"], r["biz_date"], str(r["utilisation"]), str(r["exposure"])))
ctl["hedge_fail_months"] = [(r["hedge_rel_id"], r["month_key"], str(r["dollar_offset"])) for r in hedge_rows if r["effective"] == 0 and r["assessed"] == 1]
ctl["net_position_by_tenor_day120"] = {f"{k[0]}|{k[1]}": str(v) for k, v in sorted(by_tenor.items())}
json.dump(ctl, open(os.path.join(OUT, "control_totals.json"), "w"), indent=2, default=str)
print(json.dumps({k: v for k, v in ctl.items() if k != "net_position_by_tenor_day120"}, indent=1, default=str))
