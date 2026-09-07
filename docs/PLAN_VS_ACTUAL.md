# C2 — Plan vs actual — Project 27

Classified against `OUTCOME_CONTRACT.md`. Rev 3 was the last written revision; **this document is the
Rev 4 grading** and supersedes Rev 3 where they differ.

---

## 1. Contracted components

| # | Component | Classification | Evidence (basis) |
|---|---|---|---|
| 1 | Warehouse + T-SQL engines | **Delivered as specified** | 16 source tables, 5,919 rows, 5 procedures, 120 days. Re-verified 2026-09-07: 39/39 control totals unchanged in value after a replay |
| 2 | Open mirrored DB + notebook | **Not delivered — kill executed** | Landing zone confirmed empty by the portal (404) and by its SQL endpoint. The notebook was reviewed line by line and is sound; it has never been run. One Run-all still converts this to evidenced |
| 3 | Direct Lake semantic model | **Delivered differently** | Delivered, and **more than specified**: 12 tables / 108 columns / 13 relationships / 82 measures **+ 3 calculation groups** the contract did not ask for at Rev 1. "Differently" because it took the Direct Lake **on SQL** connector, not the on-OneLake form every prior engine model used |
| 4 | Report, 4 pages | **Delivered as specified** | All four pages render in the service with values matching independently computed Warehouse figures (Position, Attribution, Credit, Hedge — read 2026-09-07 05:5x–06:0xZ). This is the first session in which the §132 gate passed on the whole report |
| 5 | Activator rules | **Not delivered — documented, not live** | No Activator/Reflex MCP tool is present in this session (established by enumerating the session's tool surface, not by assumption); `list_items` shows no `Reflex` item. Both rules and their observation windows remain specified in contract §12 |
| 6 | Variable Library + Prod replay | **Delivered as specified, and strengthened** | VL now carries 25 variables (4 added in S3, incl. the SQL endpoint that unblocked F-29). Replay **proven deterministic**: 4 EOD re-runs + hedge tests + re-freeze left all 39 control totals identical in value; only `frozen_at` moved (09-06 09:49:22 → 09-07 06:23:36) |
| 7 | SQL database probe | **Not delivered — killed S1** | A SQL database in Fabric is reachable through the DW MCP only as a read-only analytics endpoint; `Tables/Create` denied by external policy |

**Added unplanned:** three calculation groups (15 items), 32 altText narration measures,
`P27_PalmDesk_Smoke` (the render smoke test), and a `CalcGroups` verification page on
`RPT_PalmDesk_Check`. The last two are evidence artefacts, not deliverables.

---

## 2. Drift, quantified

| Measure | Planned | Actual | Note |
|---|---:|---:|---|
| Sessions | 3 | 3 | **On plan.** S3 was the contracted hard stop and held |
| Contracted components delivered | 7 | 4 | 3 killed, all with the kill criterion written before the build |
| Components killed in the session they failed | — | 3 of 3 | The contract's Phase-0 gate rule worked |
| Contract revisions | — | 4 | Rev 1 → Rev 2 (S2 status) → Rev 3 (blocker solved) → Rev 4 (this document) |
| Sessions lost to a single root cause | 0 | ~1.0 | Roughly half of S2 (4.2 h) plus the first part of S3's context, on the Direct Lake connector |

---

## 3. Which drift was avoidable, and which was discovery

**Avoidable — roughly 60% of the Direct Lake cost.** The connector was inherited from P24, where it
was proven against a **Lakehouse**, and applied to a **Warehouse** without a probe. The engine's own
standing rule already says *grep a delivered sibling, never write a shape from memory* — the failure
was that a delivered sibling **was** consulted, and the difference in source type was not treated as
a variable. This is sloppiness, and it is the project's most valuable lesson.

*Weighting basis:* S2 eliminated five hypotheses before reaching the connector. Two of those five
(framing, model size) were cheap and reasonable first checks; three (`pbism.version`,
`compatibilityLevel`, the name-form path) would not have been attempted at all had a two-table
connector probe run first. 3/5 of the diagnostic ladder ≈ 60%.

**Discovery — the rest.** That the OneLake form is a *legal* datasource kind which validates, loads
metadata and draws in the canvas while never binding a table is not documented anywhere the engine
could have read it. That could only be learned by failing. Likewise F-30/F-33 (the emit ceilings) and
F-2 (a 502 is not a rollback) are genuine platform facts obtainable only by hitting them.

**Not drift at all:** the three killed components. Each had a kill criterion written at Phase 0 and
executed on schedule. Counting them as failure would misread the contract — killing them on time is
the contract working.
