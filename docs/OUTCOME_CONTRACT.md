# Outcome Contract — Project 27 (Rev 3, measured)

> **Rev 3, 2026-09-07 — the Direct Lake blocker is SOLVED; see §13. Supersedes §12 where they differ.**
> **Rev 2, 2026-09-06, end of Session 2 — see §12 for what changed; §3 below is Rev 1 and is kept for the diff.**
> **Rev 1, 2026-09-06, end of Session 1.** Supersedes `00_Plan/OUTCOME_CONTRACT_DRAFT.md` (Rev 0.2, planning only). Every gate status below is **measured** (`00_Plan/Gate_Check_Results.md` has the tool calls); every number carries its basis and a timestamp. Format follows Skill 8 Step 0; SETTLED.md is cited, not re-derived.

**Working title:** Fabric E2E CTRM Post-Go-Live Analytics Layer — Position, MTM, P&L Attribution, Credit Exposure, Hedge Effectiveness
**Fictional client:** **Serantau Palm Trading Sdn. Bhd.** (codename PalmDesk) — collision-checked 2026-09-06 (two web searches, no match), adopted.
**Type:** D (platform estate) → Skill 8 first, then Skills 1 and 4.

---

## 1. What does *done* look like?

A Fabric estate that takes a CTRM-shaped operational store plus a vendor market-data feed and, on a single `EXEC` per business day, produces the net position by tenor, the day's mark-to-market, a six-bucket P&L attribution with a controlled unexplained residual, a counterparty credit-exposure ledger graded against limits, and an IFRS 9 hedge-effectiveness test per designated relationship. A four-page Power BI report reads live from a Direct Lake model; Activator raises the limit and unexplained-P&L alerts; a Prod workspace is produced by replaying the same definitions and scripts; a public repo + Pages guide let a reader rebuild it from empty. "Finished" = §8 graded, closure (Skill 10) written, publishing chain (Skill 9) live.

**Session 1 delivered the data plane end to end:** Warehouse loaded, engines built in T-SQL, 120 days run, control totals frozen, second implementation reconciled to the cent. See §7.

## 2. What is this for?

Portfolio piece. Public GitHub + Pages guide + portfolio card + deck, as P23–P26. Synthetic data declared in README and report footer. Built so a CTRM consultancy or a Malaysian physical-long corporate recognises its own reporting gap in it.

## 3. Components — measured status and channel

| # | Component | Channel | **Gate status (measured S1)** | Kill criterion / status |
|---|---|---|---|---|
| 1 | **Warehouse** `WH_PalmDesk` — CTRM store (`ref`/`trd`/`ops`/`mkt`, 16 tables, 5,919 rows) **and** the engines (`eng` schema: `usp_price_requests`, `usp_run_eod`, `usp_run_range`, `usp_hedge_tests`, `usp_freeze_controls`) | Core MCP (create) + **DW MCP `execute_query`** (DDL/DML/EXEC) | **✅ BUILT & PROVEN.** Gate 1 PASS with 12 controls; 120 days run; 400/400 aggregate rows + 480/480 hedge fields reconcile to the replay | — |
| 2 | **Open mirrored database** `OMD_PalmDesk_Market` (`GenericMirror`) + `NB_PalmDesk_MarketFeed` | Core MCP (create) + one notebook run via browser automation | **⚠️ CREATED, NOT REPLICATED.** Gate 2 create/read-back PASS; the notebook is authored and created; two Run-all attempts in Chrome did not register (renderer freezes on the notebook canvas at the click) | **Kill criterion executed:** the vendor feed lives in `mkt.*` Warehouse tables and the engines read them. The mirror stays as a **S2 opening item**: one click by the user (≈ 30 s) or a browser retry proves replication; if neither, the component is dropped at Rev 2 with the story unchanged |
| 3 | **Direct Lake semantic model** over the Warehouse | Core MCP `create_item` SemanticModel (TMDL) | **⚠️ CREATABLE, RENDER UNVERIFIED.** Gate 3: create PASS (13 s LRO), definition read-back PASS; the bound report card returned *"Something's wrong with one or more fields… (Gate Fact) Total Amt"* | First S2 item: prove a Direct Lake model created by API answers a query (leading hypothesis: never framed — no in-session refresh channel). Fallback unchanged: `.pbip` + one manual import |
| 4 | **Power BI report, 4 pages** | Core MCP `create_item` Report (PBIR) | **✅ CREATABLE.** Gate 4 PASS (1.3 s LRO) after the service rejected a hand-written `report.json` with JSON-path errors — a real schema validator; P26's schema versions pinned | Fallback unchanged |
| 5 | **Activator** rules | Activator remote MCP (not yet connected) or Reflex via Core MCP | [READY-TO-FIRE] per channels doc §2d; **not probed in S1** (S2 scope) | Rules documented, not live — reported, not hidden |
| 6 | **Variable Library** first item; **Prod by replay** | Core MCP + DW MCP | **✅ `VL_PalmDesk` deployed first** (21 variables, `dev`/`prod` value sets; `unexplained_tolerance_myr` frozen 0.28 at 09:49 UTC). Replay order documented in `02_Platform/WH_PalmDesk.Warehouse/README.md` | — |
| 7 | *Probe:* SQL database in Fabric as store | Core MCP + DW MCP item-scoped | **❌ FAIL — DROPPED.** Both the `SQLDatabase` id and its `SQLEndpoint` id resolve to the read-only analytics endpoint (EngineEdition 11; `Tables/Create` denied) | No regret; nothing built against it |
| 8 | *Nice-to-have:* deployment pipeline, UDF writeback, e-invoice feed | — | not started | Dropped first when time runs |
| 9 | **Excluded:** Data Agent, Ontology, Copilot authoring, Digital Twin, Fabric Maps (SETTLED) | — | — | — |

**Dated deviation from Skill 8 "Git first" (unchanged):** definitions live on disk in `02_Platform/` from first save (the folder IS the estate: VL, OMD `mirroring.json`, notebook, Warehouse DDL + procedures + replay README); the repo is published at close.

## 4. Hard constraints (measured)

| Constraint | Value | Consequence |
|---|---|---|
| **Trial capacity** | Banner **"Trials activated: 27 days left"** read **2026-09-06 04:40 UTC** (Chrome) → expiry **≈ 2026-10-03** | **E3 export before 2026-09-26**; S3 is the hard stop |
| Capacity | `14e682a7-70e3-4636-a78c-76aaa2e11be1` (`Trial-20260222T155835Z-…`, FTL64, Malaysia West) — read back via `list_capacities` | all items on it |
| Execution reach | Fabric REST / `fab` / `az` / OneLake unreachable from both shells (SETTLED 2026-09-06) | MCP connectors + browser automation only. **New S1 measurement:** the DW MCP gateway returns HTTP 502 at ≈ 100 s while the Warehouse keeps executing — long procedures run in ≤ 6-day chunks and are re-read from `eng.run_log` |
| Manual involvement | **Zero build steps needed a hand in S1.** Ledger (§10): the built-in browser was not signed in to Fabric (Chrome was — nothing asked); one usage-limit pause (resumed by the user saying "resume"); the notebook run is the only open ask, optional | Anything else is a **finding** in `00_Plan/FINDINGS_S1.md` |
| Sessions | 3 planned, 3 hard stop — **S1 used** | S2: model + report + alerts; S3: Prod replay + closure + publish |
| Terminology | FCPO/FEPO rows **VERIFIED against the Bursa pages** in S1 (`00_Plan/TERMINOLOGY.md`); delivery points and last trading day remain tagged (Product Booklet PDF not read) | tagged terms carry their tag in captions |
| Sensitivity | fictional company and 40 fictional counterparties; synthetic curves labelled synthetic on every page; no real price series | line-by-line check during S2 build |

## 5. What is true about the data (measured, seed 20260906)

| Item | Planned (Rev 0.2) | **Measured** |
|---|---|---|
| Counterparties | ~40 | **40** (16 domestic suppliers we buy CPO from; 24 refined-product buyers in IN/CN/PK/NL/DE/KE/BD/LK/PH/VN/SA/EG/MM/KR/JP/TR/TZ) |
| Physical contracts | ~600 | **549** (CPO purchases in MYR; RBDPO/PKO sales in USD; INR invoices for Indian buyers), 598 contract versions (49 amendments/cancellations) |
| Futures | ~2,500 lots | **278 trades / 3,502 lots** on the FCPO ladder (25 MT/lot, MYR 1 tick — VERIFIED), 156 closed out under the tagged expiry convention |
| Business days | 120 | **120** (Mon–Fri from 2026-03-16 to 2026-08-28; no public-holiday table — declared) |
| Curves | daily, 3 products | **2,888 rows** = 120 days × 3 products × 8 monthly tenors + 8 restated rows (CPO 2026-05-15, republished 2026-05-20); FX 240 rows (USDMYR, INRMYR); 24-month history 96 rows |
| Change stream | amendments + cancellations | 49 versions; 456 actualisations (10 % recorded late, out of sequence); 449 invoices; 119 payments |
| **Injected truth 1** — 3 mispriced trades → unexplained | on trade date only | **PC00102 2026-04-15 −312,500.00 · PC00270 2026-06-08 −120,000.00 · PC00430 2026-07-28 −201,000.00** (bucket 6 per trade); every other day ≤ 0.28 |
| **Injected truth 2** — 2 breaches on known dates | MTM route + ageing route | **CP 3 (Perusahaan Minyak Sawit Tanjung, C-grade mill, limit MYR 12.0m): BREACH from 2026-06-23**, pure MTM (5 × 5,000 MT fixed-price purchases into the June rally), peak util 1.6043 on 2026-06-29. **CP 18 (Kandla Vanaspati, limit MYR 90.0m): BREACH from 2026-07-17**, unpaid invoices (AR MYR 123.3m by 2026-08-25). **Four organic breaches also occur** (CP 25 06-04, CP 26 06-08, CP 35 06-19, CP 40 07-13) — reported, not tuned away |
| **Injected truth 3** — 1 failing hedge | known month | **Relationship 5 (RBDPO Jul-26 sale hedged with FCPO): dollar-offset −1.4366 in 2026-06** (ineffectiveness −1,740,000.00 to P&L); passes Apr (−0.8273) and May (−0.9066); prospective slope −1.0132, R² 0.8555. Seven other relationships pass every assessed month |
| Control totals | frozen with basis | `eng.control_total`, 39 rows, frozen **2026-09-06 09:49:22 UTC**; copy in `07_Exports/E1/control_total_wh.csv` |
| Restatement path | one curve correction | CPO 2026-05-15 restated on 05-20; days 45–47 re-run with `restated = 1`, day 48 recomputed; identical in both engines |

## 6. Methodology (as built — one amendment)

`00_Plan/METHODOLOGY_NOTES.md` accepted as written, with one S1 amendment recorded in Rev 1: **de minimis floor** — a month whose cumulative hedged-item change is below 1 % of the hedged notional is *not assessed* for dollar-offset (the ratio is numerically unstable near zero); prospective effectiveness carries. Bucket order new → curve → FX → time → actualisation; bucket 5 also carries amendments/cancellations; bucket 6 is the plug. Both engines implement exactly `03_Engines/replay.py`'s docstring.

## 7. Session plan — S1 done, S2/S3 unchanged

| Session | Phase | **Status** |
|---|---|---|
| 0 (2026-09-06) | Candidates, research, Rev 0.2 | done |
| **1 (2026-09-06)** | Phase 0 + 1 — gates, scaffold, sources, engines | **DONE:** banner re-read; Gate 1 PASS (12 controls); Gates 2/3/4/7 probed with three-way verdicts (7 killed); FCPO/FEPO verified; name adopted; `WS_PalmDesk_Dev` + VL + WH created; 16 tables loaded with counts = `COUNT(*)` and checksums (proven twice, after the futures and limit-rule reloads); OMD + notebook created, **replication not evidenced (kill route active)**; T-SQL engines built; 120 days + restatement run; replay reconciled to the cent (400 aggregate rows, 480 hedge fields); control totals frozen; **E1 exported** (79 files, 1,289,193 B; zip 303,062 B); contract Rev 1 |
| **2** | Phase 2 — model, report, alerts | Opens with the two S1 carry-overs: (a) prove an API-created Direct Lake model answers a query; (b) mirror replication (one click). Then TMDL model with calc groups + ~30 measures read back against rendered values, 4 pages, both validators, Activator; **E2 export** |
| **3** (hard stop) | Phase 3 — Prod replay, closure, publish | Prod = Core MCP replay of `02_Platform/` + DW MCP replay of the scripts in README order; Skill 10 C1–C8; Skill 9; lessons dual-written; **E3 before 2026-09-26** |

## 8. Exit criteria (graded at S1 close)

- [x] DW MCP: connected, `execute_query` DDL + DML + `EXEC` proven with controls; recorded as channels row 13 (12 controls, `Gate_Check_Results.md` §1)
- [x] Gates #2/#3/#4/#7 probed in S1 with three-way verdicts; kill criteria executed where failed (#7 dropped; #2 kill route active)
- [x] Warehouse: schema + data loaded; generator counts = row counts by query (16/16 tables, checksums too); control totals frozen with basis (39 rows)
- [ ] Open mirroring: `GenericMirror` DB created via Core MCP ✅; **landing-zone inserts/updates/deletes NOT evidenced** — notebook authored, run did not register; carried to S2 with the kill route already in force
- [x] Attribution: Σ six buckets = ΔMTM to the cent on **120/120 days**; |unexplained| ≤ 0.28 except on the three engineered trade dates
- [x] Exposure: two engineered breaches flagged by the right routes (2026-06-23 MTM, 2026-07-17 ageing); **Activator not yet** (S2); four organic breaches named
- [x] Hedge: relationship 5 fails in 2026-06 only; others pass; OCI roll-forward ties (reclassified 550k/3.48m/2.044m/1.161m/580.5k in the month of sale)
- [ ] Model: S2
- [ ] 4 pages: S2
- [x] Terminology: every FCPO/FEPO row VERIFIED against the Bursa pages, or tagged (2 tagged: delivery points, last trading day)
- [ ] Prod replay: S3 (README order written)
- [x] Manual-involvement ledger: **0 build actions by the user in S1**; ledger in §10
- [x] E1 on schedule (2026-09-06 10:13 UTC); E2/E3 pending
- [x] Era measurement, S1: ~1 session for Phase 0+1 (P26 needed 3); tool calls ≈ 210 in the main context + 8 subagents; browser share ≈ 25 calls (banner, Bursa ×2, gate render check, notebook ×2 — the reviewability ceiling, never a build step)

## 9. Baseline to beat

P26 VeloTrack: 7 sessions, 4 manual user actions. P27 after S1: 1 session used, 0 manual build actions (see §10).

## 10. Manual-involvement ledger (contract §4 term)

| # | Event | Who acted | Cost |
|---|---|---|---|
| 1 | Built-in browser not signed in to Fabric → the session did not enter a password; Chrome was already signed in and was used instead | nobody | 0 |
| 2 | Usage limit reached mid-load (08:00 UTC reset); the user said "pause" then "resume" | user, one word | ~0 |
| 3 | **Open:** run `NB_PalmDesk_MarketFeed` once (Fabric → WS_PalmDesk_Dev → notebook → Run all) — optional; S2 will retry by browser first | user, optional | 30 s |

## 11. Open items the user may still overrule (defaults apply otherwise)

1. Company name — adopted after the collision check.
2. Methodology — accepted, plus the de minimis floor (§6).
3. GitHub token for in-session publish — default: user's one push at close (S3).
4. The four organic breaches — default: keep them (a credit book where only the engineered names breach is not credible); the report names them as organic.

---

## 12. Rev 2 — measured status at end of Session 2 (2026-09-06)

Supersedes §3 where they differ. Every status is measured; `00_Plan/FINDINGS_S2.md` names the call.

| # | Component | **Rev 2 status** | Basis |
|---|---|---|---|
| 1 | **Warehouse + engines** | ✅ **BUILT & PROVEN** (unchanged) | S1. Extended this session by two derived tables, `ref.bucket` (6 rows) and `eng.attribution_bucket_daily` (720 rows), both verified: the unpivot sums to `sum_b` on **120 of 120 days** |
| 2 | **Open mirrored DB + notebook** | ❌ **DROPPED — kill criterion executed** | Landing zone still empty (`INFORMATION_SCHEMA.TABLES` on SQLEndpoint `0b3bb389-…` returns only `queryinsights`/`sys` — no user tables). Two more Run-all attempts today found **no toolbar element in the accessibility tree**, making four across two sessions (F-18). The vendor feed lives in `mkt.*` and the engines read it; the story is unchanged. **One human click still converts this to evidenced** — the ask is in the handover |
| 3 | **Direct Lake semantic model** | ⚠️ **BUILT, DOES NOT ANSWER — fallback taken** | `SM_PalmDesk` `f02c8481-…` exists with 12 tables, 108 columns, 13 relationships, 50 measures; create and update both Succeeded; definition reads back. Every bound visual returns **`Missing_References`**, and **a portal refresh does not fix it — the S1 "never framed" hypothesis is disproven** (F-15). Contract §3 row 3 fallback **executed**: `06_Report/P27_PalmDesk_pbip/` is a complete `.pbip` (model + report, `byPath`) needing one import |
| 4 | **Report, 4 pages** | ✅ **BUILT — as a `.pbip`, not as a service item** | `P27_PalmDesk.Report`: 4 pages, 56 visuals, 65 files, built from `_ENGINE/templates/components/`, theme `MyLifeInLegoBricks_Theme.json` (the engine default; no confirmed brand palette exists for a fictional client). `validate_pbip.py`: **0 errors**, 119 visual.json of 119 read. **Not pushed to the service**: 160,224 B of base64 is 3× the size that already failed twice today (F-17) |
| 5 | **Activator** | ❌ **NOT LIVE — rules documented** | Reaching the Activator MCP needs a user-added connector and new Entra scopes: a manual step mid-session, which §4 forbids waiting on. The Core-MCP fallback is blocked by the same payload ceiling. **Rules specified below so S3 fires them in one pass** (F-22) |
| 6 | **Variable Library + Prod replay** | ✅ unchanged | S1 |
| 7 | *Probe:* SQL database | ❌ DROPPED (unchanged) | S1, Gate 7 |

### The two Activator rules, specified (not live)

| Rule | Condition | Source | Observation window |
|---|---|---|---|
| **Credit** | `eng.exposure_daily.utilisation >= 0.90` on any counterparty-day (amber), and separately `band = 'BREACH'` | `eng.exposure_daily` | 2026-03-16 → 2026-08-28. Would fire on **6 counterparties**: engineered CP 3 (from 06-23) and CP 18 (from 07-17); **organic** CP 25 (06-04), CP 26 (06-08), CP 35 (06-19), CP 40 (07-13). 238 counterparty-days in breach; peak utilisation **2.3666** |
| **Unexplained P&L** | `ABS(eng.attribution_daily.b6) > 0.28` (the frozen `unexplained_tolerance_myr`) | `eng.attribution_daily` | Same window. Would fire on exactly **3 days**: 2026-04-15, 2026-06-08, 2026-07-28 (PC00102, PC00270, PC00430). Max |b6| = **312,499.98** |

Both windows are historical: the engines ran to 2026-08-28 and stopped, so a live Activator would
observe nothing new until the Prod replay in S3. **State that when the rules are demonstrated** —
firing them against engineered dates is a replay, not a live alert.

### §8 exit criteria — the open checkbox

Component 2's checkbox closes as **kill executed and recorded**, not as evidenced. That is the
honest reading: the protocol in `NB_PalmDesk_MarketFeed` has still never run, so its predicted row
counts (`curve` 2,879 · `fx_rate` 240 · `counterparty` 40) remain **predictions, not measurements**,
exactly as S1 flagged.

### §10 manual-involvement ledger — Session 2

| # | Step | Why it needed a hand | Cost | Status |
|---|---|---|---|---|
| 1 | Notebook Run-all | Fabric notebook ribbon is canvas-drawn (F-18, four attempts) | ~30 s of a human's time | **Open ask** |
| 2 | One portal-created Direct Lake model over `WH_PalmDesk`, to read its TMDL back as the comparator | The affordance is in the Warehouse ribbon (canvas) | ~60 s | **Open ask — highest value in S3** |
| 3 | Activator connector | Adding an MCP connector + Entra consent is user-only | one-off | **Open ask** |
| 4 | Opening the `.pbip` in Desktop for the pixel gate | No Windows shell in Cowork; the service copy cannot render (F-15) | ~2 min | **Open ask** |
| 5 | `Refresh now` on the semantic model | **Not** a manual step — done by browser from the workspace list (F-19) | 0 | Closed |

Everything above is batched into a single request at the end of `HANDOVER_S2.md`, per the
"batch those asks into one" rule.

---

## 13. Rev 3 — the blocker is solved (2026-09-07)

Supersedes §12 where they differ. `00_Plan/FINDINGS_S2.md` **F-29** and **F-30** name every call.

**The cause was the connector.** A Fabric **Warehouse** binds through **Direct Lake on SQL**
(`Sql.Database(<SQL endpoint>, <item id>)`), not Direct Lake on **OneLake**
(`AzureStorage.DataLake`). Every model this engine had built used the OneLake form, inherited from
P24's Lakehouse. One line changed; everything downstream worked.

| # | Component | **Rev 3 status** | Basis |
|---|---|---|---|
| 1 | Warehouse + engines | ✅ BUILT & PROVEN | unchanged |
| 2 | Open mirrored DB + notebook | ❌ **DROPPED — kill executed** | Landing zone confirmed empty by the portal itself (*"Failed to get landing zone files… 404"*, status Initialized) and by its SQL endpoint (*"The warehouse is empty"*). The notebook has never run. **Its code is sound** — reviewed line by line at Rev 3; the `f"abfss://{WORKSPACE_ID}@…"` lines are Python f-strings over GUIDs defined two lines above, not placeholders. One Run-all still converts this to evidenced |
| 3 | **Direct Lake semantic model** | ✅ **BUILT AND PROVEN** | `SM_PalmDesk` `f02c8481-…` — 12 tables, 108 columns, 13 relationships, 50 measures. **14 of 14 measures match Warehouse truth**; attribution residual renders **0.00**; the **zero-relationship probe passes** (six buckets, different values, summing to ΔMTM −168,330); all four warehouse schemas (`eng`/`ref`/`trd`/`mkt`) exercised |
| 4 | **Report, 4 pages** | ✅ **BUILT** · ⚠️ service copy is a 2-page smoke test until one Publish | The full report is complete and validated on disk (56 visuals, 0 validator errors) and ships as `06_Report/P27_PalmDesk_pbip/`. It **cannot** be pushed through Core MCP: 82,646 chars of array JSON against a hard ~55 KB ceiling (F-30). `P27_PalmDesk_Smoke` `ada62c43-…` deploys Position + Attribution — chosen because between them they exercise **every visual type the full report uses** — and **all render clean**, waterfall included |
| 5 | Activator | ❌ NOT LIVE — rules documented | unchanged; contract §12 carries both rules and their windows |
| 6 | Variable Library + Prod replay | ✅ unchanged | S1 |
| 7 | *Probe:* SQL database | ❌ dropped | S1 |

### §8 exit criteria — the §132 pixel gate is now SATISFIED for the visual vocabulary

All seven visual types the report uses — `waterfallChart`, `columnChart`, `lineChart`, `matrix`,
`cardVisual`, `textbox`, `pageNavigator` — render with correct values against independently computed
Warehouse figures. The two pages not deployed (Credit, Hedge) introduce **no new visual type**.
What remains unrendered is those two pages' specific bindings, not any untested mechanism.

### Environment fact added at Rev 3

`WH_PalmDesk` SQL endpoint:
`<SQL-ENDPOINT>.datawarehouse.fabric.microsoft.com`
Supplied by the user 2026-09-07; no session channel exposes it (`SERVERPROPERTY('ServerName')`
returns only the workspace GUID). **Belongs in `VL_PalmDesk`** — S3 item.

### §10 manual-involvement ledger — Rev 3

| # | Step | Status |
|---|---|---|
| 1 | Notebook Run-all | **Open** — the only thing between component 2 and evidenced |
| 2 | Portal-created comparator model | **No longer needed** — F-29 solved it without one |
| 3 | Activator connector | Open, optional |
| 4 | SQL connection string | **Closed** — supplied 2026-09-07, and it unblocked everything |
| 5 | Desktop for the pixel gate | **Closed** — satisfied in the service instead |


### Rev 3 addendum (2026-09-07) — the `.pbip` opens, and which package to use

The `$schema` defect (F-31) is fixed and **confirmed open in Desktop by the user**. Opening it
surfaced F-32: a `byPath` `.pbip` can never metadata-match a model the service has rewritten on
ingest, so Desktop always offers to overwrite. **Declined** — that would push local TMDL over the
proven live model to fix a cosmetic mismatch.

**Two packages, both kept:**

| Package | Binding | Use |
|---|---|---|
| `06_Report/P27_PalmDesk_publish/` | `byConnection` → live `SM_PalmDesk` | **Default.** Opens clean, Publish sends the 4 pages |
| `06_Report/P27_PalmDesk_pbip/` | `byPath` → local TMDL | Rebuild from scratch: fresh tenant, or post-trial |

**One Publish from the first closes component 4 completely** — and is the only route that gets all
four pages into the service, since Core MCP cannot carry them (F-30).

---

## 14. Rev 4 — CLOSED (2026-09-07, Session 3)

**Rev 4 is graded in `09_Closure/C2_Plan_vs_Actual.md`, not restated here.** §13 (Rev 3) is kept for
the diff and is superseded where the two differ.

**Summary of the grading:** 4 of 7 contracted components delivered; 3 killed against criteria written
before the build, each in the session it failed.

| # | Component | Rev 4 |
|---|---|---|
| 1 | Warehouse + engines | ✅ BUILT & PROVEN — replay **deterministic**, 39/39 control totals unchanged in value |
| 2 | Open mirrored DB + notebook | ❌ DROPPED — kill executed |
| 3 | Direct Lake model | ✅ **PROVEN and extended** — +3 calculation groups (15 items), +32 altText measures; 82 measures total |
| 4 | Report, 4 pages | ✅ **PROVEN IN THE SERVICE** — the §132 render gate passes on **all four pages** |
| 5 | Activator | ❌ documented, not live — no connector present |
| 6 | Variable Library + Prod replay | ✅ PROVEN — 25 variables (+4, incl. the SQL endpoint) |
| 7 | SQL database probe | ❌ dropped (S1) |

### Environment facts added at Rev 4

- The **Core MCP emit ceiling** is bracketed at **60,480 ✅ / 69,736 ❌** array JSON, and it is
  reached by a deliverable *growing* (F-33). The model crossed it in this session, so its 32 altText
  measures are on disk but not in the tenant.
- A second, distinct wall: the **`device_bash` result cap ≈59 KB** when reading a payload back out
  (F-34).

### §10 manual-involvement ledger — Rev 4

Six of eight hand-offs closed. **One blocking item remains:** publish
`06_Report/P27_PalmDesk_pbip/` from Desktop, accepting the model overwrite, to carry the altText
measures into the tenant. Two optional items remain (Activator connector, notebook Run-all). The full
ledger with reasons is `HANDOVER_S3.md` §6.

**Session 3 was the contracted hard stop and it held.** Closure is complete; publishing (Skill 9) is
handed off in `09_Closure/PUBLISHING_HANDOFF.md`.
