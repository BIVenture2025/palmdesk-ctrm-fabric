# PalmDesk — a CTRM post-go-live analytics layer on Microsoft Fabric

**Position · mark-to-market · six-bucket P&L attribution · counterparty credit exposure · IFRS 9 hedge effectiveness.**

A complete Microsoft Fabric estate for a commodity trading and risk management (CTRM) desk: a
Warehouse with five T-SQL engines, a Direct Lake semantic model, and a four-page Power BI report —
built end to end, deployed to a live tenant, and verified against independently computed figures
rather than against how it looked.

The fictional client is **Serantau Palm Trading Sdn. Bhd.** — a Malaysian palm oil trading company
running physical contracts hedged with Bursa Malaysia FCPO futures. **All data is synthetic**,
generated from a fixed seed (`20260906`), 120 business days. No real trades, counterparties or
prices appear anywhere in this repository.

---

## The one line that cost most of two sessions

> **A Fabric *Warehouse* binds through Direct Lake *on SQL* — `Sql.Database(<sql endpoint>, <item id>)` — not Direct Lake *on OneLake* (`AzureStorage.DataLake`).**

The OneLake form is not a syntax error. It is a **legal datasource kind**:

- it validates on create,
- it reads back byte-intact from the service,
- it passes every schema validator in the toolchain,
- and it draws all twelve tables, with their thirteen relationships, in the modelling canvas.

It simply **never binds a table**. Every visual returns `Missing_References`.

The part that makes it a lesson rather than an anecdote: **the shape had been correct twice before.**
It was copied from a delivered, working, validated sibling project — whose source was a *Lakehouse*.
A second prior project, also Direct Lake and also Lakehouse, made it look more settled still.
Repetition is not evidence.

**The rule that came out of it:** pick the Direct Lake connector from what the *source* is, and prove
it with a two-table probe before building anything on it. A shape's proof is scoped to its source
type — `docs/FINDINGS_S2.md` (F-29), `docs/INHERITED_ASSUMPTION_TESTED.md`.

The connector line is kept intact in `model/expressions.tmdl`, with only the endpoint hostname
redacted. **The shape is the point.**

---

## What was actually built

| Component | State | Evidence |
|---|---|---|
| Warehouse + 5 T-SQL engines | **Built and proven** | 39 of 39 control totals re-verified after a full replay |
| Direct Lake semantic model | **Built and proven** | 12 tables · 108 columns · 13 relationships · 82 measures · 3 calculation groups |
| 4-page Power BI report | **Rendering in the service** | Every page read against a figure computed independently in T-SQL |
| Variable Library + Prod replay | **Proven deterministic** | 39/39 control totals identical in value; only `frozen_at` moved |
| Accessibility (altText) | **32 / 32 live** | Verified by an instrument built to fail, not by looking at the report |
| Open mirrored database | **Dropped — kill executed** | Landing zone never populated. Notebook is sound and included; it was never run |
| Activator alert rules | **Documented, not live** | No Activator tool reachable in the build sessions. Rules are specified, not running |

The last two rows are stated here rather than buried. A project that says "end to end" while two
components are unfinished is describing a plan, not an estate.

### The numbers the report produces

At the last business day of the window (2026-08-28), from 120 days of synthetic history:

- book mark-to-market **MYR −168,330** across **449 open positions** — a physical long offset by a larger FCPO short, net **84,270 MT short**
- six attribution buckets summing exactly to the day's ΔMTM, with a controlled unexplained residual
- **4 of 40 counterparties** over their credit limit
- IFRS 9 effectiveness tested per designated hedge relationship

Every one of those was checked against a T-SQL query written before the render was read.

---

## Repository layout

```
model/          the semantic model as TMDL, plus the generators that produce it
                (build_tmdl.py, measures.py, calc_groups.py, alt_text.py, columns.json)
report/         the PBIR report definition and its generators
sql/            Warehouse DDL and the five engine procedures, numbered in run order
                REPLAY_ORDER.md is the sequence; source_batches/ loads the synthetic data
notebooks/      the synthetic data generator and the market-feed notebook
engines/        replay.py and reconcile.py — the second implementation used to check the first
platform/       Variable Library and mirrored-database definitions
docs/           findings, gate checks, closure pack, post-mortem, cost analysis, guide.html
```

`columns.json` is read from `INFORMATION_SCHEMA`, not written from memory — regenerating the model
needs all five files in `model/`.

---

## Rebuilding it

Full walkthrough: **[docs/guide.html](docs/guide.html)** *(rendered via GitHub Pages — from the
repository file view it will show raw markup)*.

The short version:

1. Create a Fabric workspace on a capacity, and a Warehouse in it.
2. Run `sql/000_ddl_sources.sql`, then `sql/source_batches/*.sql` in numeric order.
3. Run `sql/01_eng_tables.sql` → `sql/06_usp_freeze_controls.sql`, then the driver in
   `sql/REPLAY_ORDER.md`. Reconcile with `engines/reconcile.py` against
   `engines/control_totals.json`.
4. Put **your** warehouse's SQL endpoint into `model/expressions.tmdl` and `model/build_tmdl.py`,
   run `build_tmdl.py`, and deploy the model.
5. Build the report with `report/build_report.py` and publish it.

To generate a different dataset instead of loading the batches, run `notebooks/generate.py` — the
seed is the only thing that makes it reproducible, so change it deliberately.

---

## What is worth reading even if you never rebuild it

- **`docs/FINDINGS_S1.md` / `S2` / `S3`** — every finding with the call that established it, including the ones that cost the most.
- **`docs/POST_MORTEM.md`** — what went wrong and what it cost, including two publishes that looked identical and were not.
- **`docs/COST_ANALYSIS.md`** — measured token and time cost per session, and why the close of a session is its most expensive part per turn.
- **`docs/INHERITED_ASSUMPTION_TESTED.md`** — the reused-shape audit: 6 correct, 1 wrong from a sibling, 1 wrong from memory, 1 correct by omission.
- **`docs/CLOSURE.html`** — the whole project in five tabs.

Two findings generalise past Fabric:

**A clean render is not evidence.** A report bound to a broken model and one bound to a working model
are pixel-identical. So is a report whose 32 accessibility bindings all point at measures that do not
exist — Power BI drops them silently. Both were caught only by comparing against a value computed
somewhere else, and the second needed an instrument built specifically to fail when it was wrong.

**Verify the hand-off, not the report of the hand-off.** A `.pbip` package bound *byConnection*
carries the report only; one bound *byPath* carries the model too. Both open in Power BI Desktop,
both publish without complaint, and only one can ship a model change. The first publish here used the
wrong one, succeeded, changed nothing, and warned about none of it.

---

## Honest limitations

- Synthetic data throughout. Realistic in shape, not drawn from any real desk.
- The mirrored database and Activator rules are not live — see the table above.
- Bursa Malaysia contract specifications used by the generator are tagged VERIFIED or UNVERIFIED in
  the project's terminology notes; delivery points and last trading day were **not** verified against
  the Product Booklet and are not used by the generator.
- The tenant this was built on is a trial capacity that expires shortly after publication. Every GUID
  in this repository names something inside that trial. They are kept deliberately: they are what make
  the claims checkable rather than assertions.
- This is a portfolio build by one person over three sessions, not a production system with an
  operations team behind it.

---

## License

MIT — see [LICENSE](LICENSE).

---

Built by **Yeong Wai Son** — Kuala Lumpur, Malaysia.
Finance transformation and digital operations; Power BI, Power Platform, Azure and Fabric.
Questions or corrections: waisonyeong@gmail.com
