#!/usr/bin/env python3
"""
P27 PalmDesk — synthetic CTRM book generator (Session 1, 2026-09-06).

Fixed seed. Constants from 00_Plan/TERMINOLOGY.md (Bursa FCPO rows VERIFIED 2026-09-06).
Outputs (all under 01_Source/out/):
  data/<schema>.<table>.csv         — the tables, one CSV each (the replay engine reads these)
  sql_batches/NNN_<schema>_<table>_<k>.sql — INSERT batches, <= 1000 rows and <= ~28 KB each
  sql_batches/000_ddl.sql           — CREATE SCHEMA + CREATE TABLE (Fabric Warehouse dialect)
  manifest.json                     — per-table row counts + a checksum column sum (the count proof)
  landing/<table>/…                 — vendor-feed files for the open-mirroring notebook (parquet + _metadata.json)
Injected truths (contract §5): 3 mispriced trades, 2 counterparties breaching limits, 1 failing hedge.
Thresholds live in the Variable Library and are never tuned to the data.
"""
import csv, json, math, os, random, sys
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

SEED = 20260906
START = date(2026, 3, 16)            # Monday
N_DAYS = 120
LOT = 25                             # FCPO contract size, MT (VERIFIED Bursa)
DAILY_LIMIT = Decimal("0.10")        # FCPO 10% limit (VERIFIED Bursa)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")

rng = random.Random(SEED)
D2 = Decimal("0.01"); D3 = Decimal("0.001"); D4 = Decimal("0.0001"); D6 = Decimal("0.000001")
def q(x, qq=D2): return Decimal(x).quantize(qq, rounding=ROUND_HALF_UP)

# ---------------------------------------------------------------- calendar
def biz_days(start, n):
    out, d = [], start
    while len(out) < n:
        if d.weekday() < 5: out.append(d)
        d += timedelta(days=1)
    return out
CAL = biz_days(START, N_DAYS)
DAY_IDX = {d: i + 1 for i, d in enumerate(CAL)}
END = CAL[-1]
def month_key(d): return f"{d.year:04d}-{d.month:02d}"
def add_months(d, k):
    y, m = d.year, d.month + k
    while m > 12: y, m = y + 1, m - 12
    while m < 1: y, m = y - 1, m + 12
    return date(y, m, 1)
def month_15(mk): y, m = map(int, mk.split("-")); return date(y, m, 15)
def month_end_biz(mk):
    cands = [d for d in CAL if month_key(d) == mk]
    return cands[-1] if cands else None
MONTH_ENDS = []
for i, d in enumerate(CAL):
    if i == len(CAL) - 1 or month_key(CAL[i + 1]) != month_key(d): MONTH_ENDS.append(d)
calendar_rows = [(d.isoformat(), DAY_IDX[d], month_key(d), 1 if d in MONTH_ENDS else 0) for d in CAL]

# ---------------------------------------------------------------- products
PRODUCTS = [("CPO", "Crude palm oil (FCPO settlement curve)", "MYR", "MT"),
            ("RBDPO", "RBD palm olein (vendor assessed, FOB Malaysia)", "USD", "MT"),
            ("PKO", "Palm kernel oil (vendor assessed, FOB Malaysia)", "USD", "MT")]

# ---------------------------------------------------------------- curves (vendor feed)
# Deterministic daily paths: CPO spot in MYR/MT integers (tick MYR 1.00); RBDPO/PKO USD/MT 2dp.
# A rally in CPO over days 66-74 (+~12%) is the credit-breach driver; a refined-basis collapse in
# June is the hedge-failure driver. Neither threshold is tuned to them.
def gen_paths():
    cpo, rbd, pko = Decimal(3950), Decimal("975.00"), Decimal("1320.00")
    usdmyr, inrmyr = Decimal("4.430000"), Decimal("0.052900")
    paths = []
    for i, d in enumerate(CAL, start=1):
        drift = Decimal(0)
        if 66 <= i <= 74: drift = Decimal("0.016")          # rally: ~+12% over 9 days
        if 90 <= i <= 96: drift = Decimal("-0.006")          # partial give-back
        shock = Decimal(rng.gauss(0, 0.009)).quantize(D6)
        move = max(-DAILY_LIMIT, min(DAILY_LIMIT, drift + shock))
        cpo = q(cpo * (1 + move), Decimal(1))
        # refined basis: RBDPO tracks CPO/USDMYR + basis; basis collapses in June (days 56-63)
        basis = Decimal("62.00")
        if 56 <= i <= 63: basis = Decimal("62.00") - Decimal(i - 55) * Decimal("9.5")
        elif i > 63: basis = Decimal("-14.00") + Decimal(min(i - 63, 25)) * Decimal("2.4")
        rbd = q(cpo / usdmyr + basis + Decimal(rng.gauss(0, 4)))
        pko = q(pko * (1 + Decimal(rng.gauss(0, 0.007))))
        usdmyr = q(usdmyr * (1 + Decimal(rng.gauss(0, 0.0025)) + (Decimal("0.0012") if 56 <= i <= 63 else Decimal(0))), D6)
        inrmyr = q(inrmyr * (1 + Decimal(rng.gauss(0, 0.002))), D6)
        paths.append((d, cpo, rbd, pko, usdmyr, inrmyr))
    return paths
PATHS = gen_paths()
SPOT = {p[0]: p for p in PATHS}

def tenor_months(d):
    m0 = date(d.year, d.month, 1)
    return [month_key(add_months(m0, k)) for k in range(8)]
TENORS = {d: tenor_months(d) for d in CAL}

curve_rows = []      # (curve_date, product, tenor_month, price, published_at, version)
CURVE = {}           # (product, date, tenor_month) -> price (version 1)
for (d, cpo, rbd, pko, usdmyr, inrmyr) in PATHS:
    for k, tm in enumerate(TENORS[d]):
        # contango shape: +0.45%/month for CPO, +0.35% for USD products, deterministic per day
        c = q(cpo * (1 + Decimal("0.0045") * k), Decimal(1))
        r = q(rbd * (1 + Decimal("0.0035") * k))
        p = q(pko * (1 + Decimal("0.0030") * k))
        for prod, px in (("CPO", c), ("RBDPO", r), ("PKO", p)):
            curve_rows.append((d.isoformat(), prod, tm, str(px), d.isoformat(), 1))
            CURVE[(prod, d, tm)] = px
# Restatement: CPO curve for day 45 republished on day 48 (version 2), every tenor -18 MYR
RESTATE_DAY, RESTATE_PUB = CAL[44], CAL[47]
RESTATED = {}
for tm in TENORS[RESTATE_DAY]:
    px = CURVE[("CPO", RESTATE_DAY, tm)] - Decimal(18)
    curve_rows.append((RESTATE_DAY.isoformat(), "CPO", tm, str(px), RESTATE_PUB.isoformat(), 2))
    RESTATED[tm] = px
# Withdrawn quote (delete in the vendor feed): PKO tenor m7 on day 30 is withdrawn on day 31 (mirror-only event)
WITHDRAWN = ("PKO", CAL[29], TENORS[CAL[29]][7])

fx_rows = [(d.isoformat(), "USDMYR", str(u)) for (d, _, _, _, u, _) in PATHS] + \
          [(d.isoformat(), "INRMYR", str(i)) for (d, _, _, _, _, i) in PATHS]
FX = {("USDMYR", d): u for (d, _, _, _, u, _) in PATHS}
FX.update({("INRMYR", d): i for (d, _, _, _, _, i) in PATHS})
FX.update({("MYR", d): Decimal("1.000000") for d in CAL})
FX.update({("USD", d): FX[("USDMYR", d)] for d in CAL})
FX.update({("INR", d): FX[("INRMYR", d)] for d in CAL})

# 24 months of monthly history before the window (hedge prospective regression)
hist_rows = []
hc, hr, hp, hu = Decimal(3600), Decimal("880.00"), Decimal("1200.00"), Decimal("4.55")
for k in range(24):
    mk = month_key(add_months(date(2024, 3, 1), k))
    mv = Decimal(rng.gauss(0, 0.035))
    hc = q(hc * (1 + mv), Decimal(1))
    hr = q(hc / hu + Decimal(60) + Decimal(rng.gauss(0, 7)))      # refined tracks crude, noisy basis
    hp = q(hp * (1 + Decimal(rng.gauss(0, 0.03)) + mv * Decimal("0.4")))
    hu = q(hu * (1 + Decimal(rng.gauss(0, 0.006))), D6)
    hist_rows += [(mk, "CPO", str(hc), "MYR"), (mk, "RBDPO", str(hr), "USD"), (mk, "PKO", str(hp), "USD"),
                  (mk, "USDMYR", str(hu), "FX")]

# ---------------------------------------------------------------- counterparties
SUPPLIERS = [  # domestic mills / plantations we BUY CPO from (MYR)
 ("Kilang Sawit Sungai Rengit Sdn Bhd","MY"),("Ladang Bukit Kemuning Berhad","MY"),("Perusahaan Minyak Sawit Tanjung Sdn Bhd","MY"),
 ("Kilang Kelapa Sawit Lembah Beringin Sdn Bhd","MY"),("Estet Seri Gading Sdn Bhd","MY"),("Sawit Bersatu Pahang Sdn Bhd","MY"),
 ("Kilang Sawit Ulu Tembeling Sdn Bhd","MY"),("Perladangan Nusa Damai Berhad","MY"),("Sri Kenanga Palm Mills Sdn Bhd","MY"),
 ("Kilang Sawit Kuala Rompin Sdn Bhd","MY"),("Ladang Gunung Ledang Sdn Bhd","MY"),("Sawit Emas Johor Sdn Bhd","MY"),
 ("Kilang Minyak Sawit Segamat Sdn Bhd","MY"),("Estet Bukit Rotan Sdn Bhd","MY"),("Perusahaan Sawit Merbok Sdn Bhd","MY"),
 ("Kilang Sawit Teluk Intan Sdn Bhd","MY")]
BUYERS = [  # refined-product buyers (USD invoices; IN buyers invoiced in INR)
 ("Mundra Edible Oils Pvt Ltd","IN"),("Kandla Vanaspati Industries Ltd","IN"),("Saurashtra Oil Refiners Pvt Ltd","IN"),("Chennai Agro Fats Ltd","IN"),
 ("Zhangjiagang Yuhua Grain & Oil Co","CN"),("Tianjin Haihe Oils Trading Co","CN"),("Guangzhou Nanhai Fats Co","CN"),
 ("Karachi Vegetable Ghee Mills Ltd","PK"),("Lahore Banaspati Industries Ltd","PK"),("Port Qasim Oils Ltd","PK"),
 ("Rotterdam Fats Trading BV","NL"),("Hamburg Speiseoel Handels GmbH","DE"),("Nairobi Edible Oils Ltd","KE"),
 ("Dhaka Refined Oils Ltd","BD"),("Colombo Oils & Fats Pvt Ltd","LK"),("Manila Coconut & Palm Co","PH"),
 ("Ho Chi Minh Vegetable Oils JSC","VN"),("Jeddah Fats & Oils Trading","SA"),("Alexandria Oil Refiners SAE","EG"),
 ("Yangon Edible Oils Co","MM"),("Busan Oils Trading Co","KR"),("Osaka Fats Import KK","JP"),("Istanbul Bitkisel Yag AS","TR"),
 ("Dar es Salaam Edible Oils Ltd","TZ")]
cp_rows = []; CP = {}
cid = 0
for name, ctry in SUPPLIERS:
    cid += 1
    grade = rng.choice("AABBBC"); cp_rows.append((cid, f"CP{cid:03d}", name, ctry, "SUPPLIER", grade, 1 if rng.random() < 0.5 else 0, rng.choice([7, 14, 30]), 0))
for name, ctry in BUYERS:
    cid += 1
    grade = rng.choice("ABBBCCD"); cp_rows.append((cid, f"CP{cid:03d}", name, ctry, "BUYER", grade, 1 if rng.random() < 0.35 else 0, rng.choice([30, 45, 60]), 1 if rng.random() < 0.6 else 0))
for r in cp_rows: CP[r[0]] = r
CP_A = 3      # Perusahaan Minyak Sawit Tanjung — MTM-route breach (we buy big, curve rallies)
CP_B = 18     # Kandla Vanaspati — ageing-route breach (unpaid invoices)
# scenario attributes are DATA (a mid-tier mill, a cash-against-documents buyer); the limit RULE above is not touched
cp_rows[CP_A - 1] = cp_rows[CP_A - 1][:5] + ("C",) + cp_rows[CP_A - 1][6:]
cp_rows[CP_B - 1] = cp_rows[CP_B - 1][:5] + ("C",) + cp_rows[CP_B - 1][6:8] + (0,)
CP[CP_A] = cp_rows[CP_A - 1]; CP[CP_B] = cp_rows[CP_B - 1]
N_CP = len(cp_rows)
limit_rows = []
for r in cp_rows:
    # Limit rule (uniform, never tuned to a scenario): buyers carry cargo-scale limits because a
    # cargo delivered before payment is full-value exposure; suppliers carry replacement-cost limits.
    base = ({"A": 150, "B": 110, "C": 75, "D": 40} if r[4] == "BUYER" else {"A": 25, "B": 15, "C": 8, "D": 4})[r[5]]
    lim = Decimal(base) * Decimal(10 ** 6) * Decimal(rng.choice([0.8, 1.0, 1.2, 1.5]))
    limit_rows.append((r[0], str(q(lim))))
LIMIT = {a: Decimal(b) for a, b in limit_rows}
coll_rows = []
for r in cp_rows:
    if r[4] == "BUYER" and rng.random() < 0.5:
        typ = rng.choice(["LC", "LC", "BG", "CASH"])
        coll_rows.append((r[0], typ, str(q(LIMIT[r[0]] * Decimal(rng.choice([0.1, 0.15, 0.25]))))))
ecl_rows = []
for g, base in (("A", "0.0020"), ("B", "0.0060"), ("C", "0.0150"), ("D", "0.0400")):
    for band, mult in (("0-30", 1), ("31-60", 3), ("61-90", 8), ("90+", 25)):
        ecl_rows.append((g, band, str(q(Decimal(base) * mult, D4))))

# ---------------------------------------------------------------- physical contracts
TERMS_BUY = ["FOB Port Klang", "FOB Pasir Gudang", "FOB Lahad Datu"]
TERMS_SELL = ["CNF Mundra", "CNF Kandla", "CNF Zhangjiagang", "CNF Karachi", "FOB Port Klang", "FOB Pasir Gudang"]
def interp_price(prod, d, delivery):
    """Vendor curve interpolated at tenor days — same rule as the engines (points at the 15th)."""
    pts = [(( month_15(tm) - d).days, CURVE[(prod, d, tm)]) for tm in TENORS[d]]
    tau = (delivery - d).days
    if tau <= pts[0][0]: return pts[0][1]
    if tau >= pts[-1][0]: return pts[-1][1]
    for (t0, p0), (t1, p1) in zip(pts, pts[1:]):
        if t0 <= tau <= t1:
            return q((p0 * (t1 - tau) + p1 * (tau - t0)) / Decimal(t1 - t0), D4)
contract_rows, version_rows, actual_rows, invoice_rows, payment_rows = [], [], [], [], []
CONTRACTS = {}
cno = 0
MISPRICED_DAYS = {23, 61, 97}       # injected truth 1: booked price != confirmed price
mispriced_refs = []
def new_contract(d, cp_id, prod, side, qty, price, ccy, delivery, terms, mispriced=False):
    global cno
    cno += 1
    ref = f"PC{cno:05d}"
    booked = price
    confirmed = price
    if mispriced:
        booked = q(price * Decimal("1.0300"), Decimal(1) if ccy == "MYR" else D2)   # fat-fingered booking
        mispriced_refs.append(ref)
    is_mspo = 1 if rng.random() < 0.92 else 0
    contract_rows.append((cno, ref, cp_id, prod, side, d.isoformat(), delivery.isoformat(), ccy, terms, is_mspo, str(confirmed), str(qty)))
    version_rows.append((cno, 1, d.isoformat(), str(qty), str(booked), "OPEN", "NEW"))
    CONTRACTS[cno] = dict(ref=ref, cp=cp_id, prod=prod, side=side, trade=d, delivery=delivery, ccy=ccy, qty=qty, price=booked, versions=[(d, qty, booked, "OPEN")])
    return cno
supplier_ids = [r[0] for r in cp_rows if r[4] == "SUPPLIER"]
buyer_ids = [r[0] for r in cp_rows if r[4] == "BUYER"]
for d in CAL:
    i = DAY_IDX[d]
    n_buy = rng.choice([1, 2, 2, 3]); n_sell = rng.choice([2, 2, 3, 3])
    for _ in range(n_buy):
        cp = rng.choice(supplier_ids)
        delivery = d + timedelta(days=rng.randint(10, 75))
        qty = Decimal(rng.choice([500, 1000, 1500, 2000, 2500]))
        px = interp_price("CPO", d, delivery) + Decimal(rng.randint(-25, 25))
        new_contract(d, cp, "CPO", "B", qty, q(px, Decimal(1)), "MYR", delivery, rng.choice(TERMS_BUY), mispriced=(i in MISPRICED_DAYS and _ == 0))
    for _ in range(n_sell):
        cp = rng.choice(buyer_ids)
        prod = rng.choice(["RBDPO", "RBDPO", "RBDPO", "PKO"])
        delivery = d + timedelta(days=rng.randint(15, 90))
        qty = Decimal(rng.choice([500, 1000, 1500, 2000, 3000]))
        px = interp_price(prod, d, delivery) + Decimal(rng.randint(-15, 15))
        new_contract(d, cp, prod, "S", qty, q(px), "USD", delivery, rng.choice(TERMS_SELL))
# Injected truth 2a: CP_A sells us five large fixed-price CPO cargoes just before the rally
for k in range(5):
    d = CAL[60 + k]
    new_contract(d, CP_A, "CPO", "B", Decimal(5000), q(interp_price("CPO", d, d + timedelta(days=55)) - Decimal(10), Decimal(1)), "MYR", d + timedelta(days=55), "FOB Pasir Gudang")
# Injected truth 2b: CP_B buys refined oil in March/April and never pays the invoices
for k in range(4):
    d = CAL[3 + 4 * k]; dl = d + timedelta(days=25 + 20 * k)
    new_contract(d, CP_B, "RBDPO", "S", Decimal(4000), q(interp_price("RBDPO", d, dl)), "USD", dl, "CNF Kandla")
CP_B_CONTRACTS = [c for c, v in CONTRACTS.items() if v["cp"] == CP_B]

# amendments and cancellations (change stream; bucket 5 + vendor-feed style updates)
for c, v in list(CONTRACTS.items()):
    if v["cp"] in (CP_A, CP_B): continue
    r = rng.random()
    if r < 0.08:   # quantity amendment 3-12 business days after trade
        k = DAY_IDX[v["trade"]] + rng.randint(3, 12)
        if k <= N_DAYS and CAL[k - 1] < v["delivery"]:
            nq = q(v["qty"] * Decimal(rng.choice(["0.8", "0.9", "1.1", "1.2"])), D3)
            version_rows.append((c, 2, CAL[k - 1].isoformat(), str(nq), str(v["price"]), "OPEN", "AMEND_QTY"))
            v["versions"].append((CAL[k - 1], nq, v["price"], "OPEN"))
    elif r < 0.11:  # cancellation
        k = DAY_IDX[v["trade"]] + rng.randint(2, 8)
        if k <= N_DAYS and CAL[k - 1] < v["delivery"]:
            version_rows.append((c, 2, CAL[k - 1].isoformat(), "0.000", str(v["price"]), "CANCELLED", "CANCEL"))
            v["versions"].append((CAL[k - 1], Decimal(0), v["price"], "CANCELLED"))

def version_at(v, d):
    cur = None
    for (vd, qty, px, st) in v["versions"]:
        if vd <= d: cur = (qty, px, st)
    return cur
def biz_on_or_after(dt):
    for d in CAL:
        if d >= dt: return d
    return None

# actualisations (deliveries), invoices, payments
ano = ino = pno = 0
for c, v in CONTRACTS.items():
    if v["delivery"] > END: continue
    qty, px, st = version_at(v, v["delivery"])
    if st != "OPEN": continue
    ad = biz_on_or_after(v["delivery"])
    if ad is None: continue
    # partial or full, with quality/quantity difference vs contract
    if v["cp"] == CP_A: parts = [qty]
    elif rng.random() < 0.2: parts = [q(qty * Decimal("0.6"), D3), q(qty * Decimal("0.4"), D3)]
    else: parts = [qty]
    for j, pq in enumerate(parts):
        ano += 1
        dd = ad if j == 0 else biz_on_or_after(ad + timedelta(days=rng.randint(3, 9)))
        if dd is None: continue
        aq = q(pq * Decimal(rng.choice(["1.000", "1.000", "0.995", "1.004", "0.990"])), D3)
        apx = px if v["cp"] == CP_A else q(px + Decimal(rng.choice([0, 0, 0, -2, 3])), Decimal(1) if v["ccy"] == "MYR" else D2)
        qadj = Decimal(rng.choice(["0.0000", "0.0000", "0.0000", "-0.0050", "-0.0120"]))
        late = rng.random() < 0.10   # dirty data: recorded late, out of sequence
        rec = biz_on_or_after(dd + timedelta(days=rng.randint(2, 5))) if late else dd
        if rec is None: rec = END
        actual_rows.append((ano, c, dd.isoformat(), str(aq), str(apx), str(qadj), rec.isoformat()))
        # invoice raised 1-3 business days after actualisation
        inv_d = biz_on_or_after(dd + timedelta(days=rng.randint(1, 3)))
        if inv_d is None: continue
        ino += 1
        terms = CP[v["cp"]][7]
        due = inv_d + timedelta(days=terms)
        amt_ccy = q(aq * apx * (1 + qadj))
        inv_ccy = "INR" if CP[v["cp"]][3] == "IN" and v["ccy"] == "USD" else v["ccy"]
        if inv_ccy == "INR": amt_ccy = q(amt_ccy * FX[("USDMYR", inv_d)] / FX[("INRMYR", inv_d)])
        amt_myr = q(amt_ccy * FX[(inv_ccy, inv_d)])
        invoice_rows.append((ino, c, v["cp"], inv_d.isoformat(), due.isoformat(), inv_ccy, str(amt_ccy), str(amt_myr), v["side"]))
        # payment: buyers pay us; we pay suppliers (only receivables matter for exposure -> side 'S')
        if v["cp"] == CP_B: continue                       # injected truth 2b: never paid
        if v["side"] == "S":
            grade = CP[v["cp"]][5]
            lag = rng.choice({"A": [-2, 0, 3], "B": [0, 5, 12], "C": [7, 20, 45], "D": [15, 40, 70]}[grade])
            pd_ = biz_on_or_after(due + timedelta(days=lag))
            if pd_ is not None and pd_ <= END:
                pno += 1
                payment_rows.append((pno, ino, pd_.isoformat(), str(amt_myr)))

# ---------------------------------------------------------------- hedge relationships + futures
hedge_rows = []; HEDGES = {}
designs = [  # (product, forecast month, tonnes, designation day index)
    ("CPO", "2026-06", 5000, 1), ("CPO", "2026-07", 6000, 1), ("CPO", "2026-08", 4000, 1), ("CPO", "2026-09", 5000, 12),
    ("RBDPO", "2026-07", 3000, 1),      # injected truth 3: refined sale hedged with crude futures, basis blows out in June
    ("CPO", "2026-08", 3000, 25), ("CPO", "2026-08", 1500, 25), ("CPO", "2026-09", 2500, 40)]
for h, (prod, fm, tonnes, di) in enumerate(designs, start=1):
    lots = int(round(tonnes / LOT))
    ratio = q(Decimal(lots * LOT) / Decimal(tonnes), D4)
    hedge_rows.append((h, CAL[di - 1].isoformat(), prod, fm, str(Decimal(tonnes)), lots, str(ratio), 1, "CASH_FLOW"))
    HEDGES[h] = dict(prod=prod, fm=fm, tonnes=Decimal(tonnes), lots=lots, dday=CAL[di - 1])

fut_rows = []; fno = 0
def fut(d, cm, side, lots, px, hedge=None):
    global fno
    fno += 1
    # expiry convention (TERMINOLOGY.md, tagged): closed out on the last business day of the month before the contract month
    y, m = map(int, cm.split("-")); prev = add_months(date(y, m, 1), -1)
    close = month_end_biz(month_key(prev))
    close_px = CURVE[("CPO", close, cm)] if close and close > d and close <= END else None
    fut_rows.append((fno, f"FT{fno:05d}", d.isoformat(), cm, side, lots, str(px), hedge, (close.isoformat() if close_px is not None else None), (str(close_px) if close_px is not None else None)))
for h, hv in HEDGES.items():
    fut(hv["dday"], hv["fm"], "S", hv["lots"], CURVE[("CPO", hv["dday"], hv["fm"])], hedge=h)
for d in CAL:
    for _ in range(rng.choice([1, 2, 2, 3, 4])):
        # never trade a month whose close-out (last biz day of the preceding month) is already past
        k = rng.randint(1, 6)
        if month_end_biz(month_key(d)) is not None and (month_end_biz(month_key(d)) - d).days < 4 and k == 1: k = 2
        cm = TENORS[d][k]
        side = rng.choice("BSSB")
        lots = rng.choice([2, 4, 4, 6, 8, 10, 12, 20])
        px = CURVE[("CPO", d, cm)] + Decimal(rng.randint(-6, 6))
        fut(d, cm, side, lots, q(px, Decimal(1)))

# ---------------------------------------------------------------- write outputs
os.makedirs(os.path.join(OUT, "data"), exist_ok=True)
os.makedirs(os.path.join(OUT, "sql_batches"), exist_ok=True)
TABLES = {
 "ref.calendar": (["biz_date", "day_index", "month_key", "is_month_end"], calendar_rows),
 "ref.product": (["product_code", "product_name", "curve_ccy", "unit"], PRODUCTS),
 "ref.counterparty": (["cp_id", "cp_code", "cp_name", "country", "segment", "grade", "has_netting", "payment_terms_days", "we_deliver_first"], cp_rows),
 "ref.credit_limit": (["cp_id", "approved_limit_myr"], limit_rows),
 "ref.collateral": (["cp_id", "collateral_type", "amount_myr"], coll_rows),
 "ref.ecl_rate": (["grade", "ageing_band", "rate"], ecl_rows),
 "trd.physical_contract": (["contract_id", "contract_ref", "cp_id", "product_code", "side", "trade_date", "delivery_date", "price_ccy", "terms", "is_mspo", "confirmed_price", "confirmed_qty_mt"], contract_rows),
 "trd.contract_version": (["contract_id", "version_no", "valid_from", "quantity_mt", "price", "status", "change_reason"], version_rows),
 "trd.futures_trade": (["trade_id", "trade_ref", "trade_date", "contract_month", "side", "lots", "price_myr", "hedge_rel_id", "close_date", "close_price"], fut_rows),
 "trd.hedge_relationship": (["hedge_rel_id", "designation_date", "product_code", "forecast_month", "forecast_qty_mt", "designated_lots", "hedge_ratio", "documented", "hedge_type"], hedge_rows),
 "ops.actualisation": (["actual_id", "contract_id", "actual_date", "quantity_mt", "actual_price", "quality_adj_pct", "recorded_date"], actual_rows),
 "ops.invoice": (["invoice_id", "contract_id", "cp_id", "invoice_date", "due_date", "currency", "amount_ccy", "amount_myr", "side"], invoice_rows),
 "ops.payment": (["payment_id", "invoice_id", "payment_date", "amount_myr"], payment_rows),
 "mkt.curve": (["curve_date", "product_code", "tenor_month", "price", "published_at", "version"], curve_rows),
 "mkt.fx_rate": (["rate_date", "ccy_pair", "rate"], fx_rows),
 "mkt.monthly_history": (["month_key", "series", "price", "unit"], hist_rows),
}
DDL_TYPES = {
 "ref.calendar": "biz_date DATE NOT NULL, day_index INT NOT NULL, month_key CHAR(7) NOT NULL, is_month_end BIT NOT NULL",
 "ref.product": "product_code VARCHAR(8) NOT NULL, product_name VARCHAR(60) NOT NULL, curve_ccy CHAR(3) NOT NULL, unit VARCHAR(4) NOT NULL",
 "ref.counterparty": "cp_id INT NOT NULL, cp_code VARCHAR(10) NOT NULL, cp_name VARCHAR(80) NOT NULL, country CHAR(2) NOT NULL, segment VARCHAR(10) NOT NULL, grade CHAR(1) NOT NULL, has_netting BIT NOT NULL, payment_terms_days INT NOT NULL, we_deliver_first BIT NOT NULL",
 "ref.credit_limit": "cp_id INT NOT NULL, approved_limit_myr DECIMAL(18,2) NOT NULL",
 "ref.collateral": "cp_id INT NOT NULL, collateral_type VARCHAR(5) NOT NULL, amount_myr DECIMAL(18,2) NOT NULL",
 "ref.ecl_rate": "grade CHAR(1) NOT NULL, ageing_band VARCHAR(6) NOT NULL, rate DECIMAL(8,4) NOT NULL",
 "trd.physical_contract": "contract_id INT NOT NULL, contract_ref VARCHAR(10) NOT NULL, cp_id INT NOT NULL, product_code VARCHAR(8) NOT NULL, side CHAR(1) NOT NULL, trade_date DATE NOT NULL, delivery_date DATE NOT NULL, price_ccy CHAR(3) NOT NULL, terms VARCHAR(20) NOT NULL, is_mspo BIT NOT NULL, confirmed_price DECIMAL(12,2) NOT NULL, confirmed_qty_mt DECIMAL(12,3) NOT NULL",
 "trd.contract_version": "contract_id INT NOT NULL, version_no INT NOT NULL, valid_from DATE NOT NULL, quantity_mt DECIMAL(12,3) NOT NULL, price DECIMAL(12,2) NOT NULL, status VARCHAR(10) NOT NULL, change_reason VARCHAR(10) NOT NULL",
 "trd.futures_trade": "trade_id INT NOT NULL, trade_ref VARCHAR(10) NOT NULL, trade_date DATE NOT NULL, contract_month CHAR(7) NOT NULL, side CHAR(1) NOT NULL, lots INT NOT NULL, price_myr DECIMAL(12,2) NOT NULL, hedge_rel_id INT NULL, close_date DATE NULL, close_price DECIMAL(12,2) NULL",
 "trd.hedge_relationship": "hedge_rel_id INT NOT NULL, designation_date DATE NOT NULL, product_code VARCHAR(8) NOT NULL, forecast_month CHAR(7) NOT NULL, forecast_qty_mt DECIMAL(12,3) NOT NULL, designated_lots INT NOT NULL, hedge_ratio DECIMAL(8,4) NOT NULL, documented BIT NOT NULL, hedge_type VARCHAR(10) NOT NULL",
 "ops.actualisation": "actual_id INT NOT NULL, contract_id INT NOT NULL, actual_date DATE NOT NULL, quantity_mt DECIMAL(12,3) NOT NULL, actual_price DECIMAL(12,2) NOT NULL, quality_adj_pct DECIMAL(8,4) NOT NULL, recorded_date DATE NOT NULL",
 "ops.invoice": "invoice_id INT NOT NULL, contract_id INT NOT NULL, cp_id INT NOT NULL, invoice_date DATE NOT NULL, due_date DATE NOT NULL, currency CHAR(3) NOT NULL, amount_ccy DECIMAL(18,2) NOT NULL, amount_myr DECIMAL(18,2) NOT NULL, side CHAR(1) NOT NULL",
 "ops.payment": "payment_id INT NOT NULL, invoice_id INT NOT NULL, payment_date DATE NOT NULL, amount_myr DECIMAL(18,2) NOT NULL",
 "mkt.curve": "curve_date DATE NOT NULL, product_code VARCHAR(8) NOT NULL, tenor_month CHAR(7) NOT NULL, price DECIMAL(12,2) NOT NULL, published_at DATE NOT NULL, version INT NOT NULL",
 "mkt.fx_rate": "rate_date DATE NOT NULL, ccy_pair CHAR(6) NOT NULL, rate DECIMAL(12,6) NOT NULL",
 "mkt.monthly_history": "month_key CHAR(7) NOT NULL, series VARCHAR(8) NOT NULL, price DECIMAL(12,6) NOT NULL, unit CHAR(3) NOT NULL",
}
CHECK_COL = {"ref.calendar": "day_index", "ref.product": None, "ref.counterparty": "cp_id", "ref.credit_limit": "approved_limit_myr",
 "ref.collateral": "amount_myr", "ref.ecl_rate": "rate", "trd.physical_contract": "confirmed_qty_mt", "trd.contract_version": "quantity_mt",
 "trd.futures_trade": "lots", "trd.hedge_relationship": "designated_lots", "ops.actualisation": "quantity_mt", "ops.invoice": "amount_myr",
 "ops.payment": "amount_myr", "mkt.curve": "price", "mkt.fx_rate": "rate", "mkt.monthly_history": "price"}

def sql_lit(v):
    if v is None: return "NULL"
    if isinstance(v, (int,)): return str(v)
    if isinstance(v, Decimal): return str(v)
    s = str(v)
    return "'" + s.replace("'", "''") + "'"
manifest = {"seed": SEED, "start": START.isoformat(), "end": END.isoformat(), "n_days": N_DAYS, "tables": {}, "batches": [],
            "injected": {"mispriced_contract_refs": mispriced_refs, "cp_mtm_breach": CP_A, "cp_ageing_breach": CP_B,
                         "cp_b_contract_ids": CP_B_CONTRACTS, "failing_hedge_rel_id": 5,
                         "restated_curve_date": RESTATE_DAY.isoformat(), "restated_published": RESTATE_PUB.isoformat(),
                         "withdrawn_quote": [WITHDRAWN[0], WITHDRAWN[1].isoformat(), WITHDRAWN[2]]}}
ddl = ["CREATE SCHEMA ref;", "CREATE SCHEMA trd;", "CREATE SCHEMA ops;", "CREATE SCHEMA mkt;", "CREATE SCHEMA eng;"]
seq = 1
for tname, (cols, rows) in TABLES.items():
    with open(os.path.join(OUT, "data", tname + ".csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(cols); w.writerows(rows)
    ddl.append(f"CREATE TABLE {tname} ({DDL_TYPES[tname]});")
    # numeric checksum: sum of check column, as Decimal string
    cc = CHECK_COL[tname]
    chk = None
    if cc:
        ix = cols.index(cc); chk = str(sum(Decimal(str(r[ix])) for r in rows if r[ix] is not None))
    manifest["tables"][tname] = {"rows": len(rows), "check_column": cc, "check_sum": chk}
    # batches
    head = f"INSERT INTO {tname} ({', '.join(cols)}) VALUES "
    i = 0; k = 0
    while i < len(rows):
        chunk, size = [], len(head)
        while i < len(rows) and len(chunk) < 1000:
            lit = "(" + ",".join(sql_lit(v) for v in rows[i]) + ")"
            if size + len(lit) + 1 > 28000 and chunk: break
            chunk.append(lit); size += len(lit) + 1; i += 1
        k += 1
        fn = f"{seq:03d}_{tname.replace('.', '_')}_{k}.sql"
        body = head + ",".join(chunk) + ";"
        open(os.path.join(OUT, "sql_batches", fn), "w").write(body)
        manifest["batches"].append({"file": fn, "table": tname, "rows": len(chunk), "bytes": len(body)})
        seq += 1
open(os.path.join(OUT, "sql_batches", "000_ddl.sql"), "w").write("\n".join(ddl) + "\n")
json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w"), indent=2)
print(json.dumps({t: v["rows"] for t, v in manifest["tables"].items()}, indent=1))
print("batches:", len(manifest["batches"]), "total bytes:", sum(b["bytes"] for b in manifest["batches"]))
print("mispriced:", mispriced_refs, "| CP_A", CP_A, "| CP_B", CP_B, "| failing hedge 5 (RBDPO/2026-07)")
