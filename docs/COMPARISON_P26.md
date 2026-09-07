# C3 — Comparison against the previous comparable project

**Project 27 (PalmDesk) vs Project 26 (VeloTrack) · written Session 3, 2026-09-07**

---

## 0. Establishing which project this is — and the first thing that check caught

Skill 10 C3 opens with a warning: do not trust the folder name, the `CLAUDE.md` row, or the
project's own status document.

**Following that instruction immediately found a defect in `CLAUDE.md` itself.**

> `CLAUDE.md`, Project Type Fork: *"Type D so far: 23 (Nordhaus O2C) · 24 (GlobalEnergy FP&A) ·
> 25 (Meridian Pay RTI)."*

That list is **stale — it omits Project 26**. `26) Fabric E2E Live Logistics & Fleet Telemetry
(VeloTrack)`, `OUTCOME_CONTRACT.md` line 10, reads *"Type D (platform build) · opened 2026-08-20"*,
and its §3 component list carries a Lakehouse, Materialized Lake Views, an ML model, an Ontology, a
**Direct Lake semantic model** and a **four-page report**. It is unambiguously Type D and it is the
project immediately before this one.

**This document was first drafted against Project 25 on the strength of that CLAUDE.md row, and was
rewritten once the row was checked.** That is the C3 trap working exactly as the skill describes,
and it is why the check is worth the ten minutes. The stale row is dual-written as a correction (see
C5) rather than quietly fixed here.

| Question | Answer | Basis |
|---|---|---|
| Previous comparable project | **Project 26, VeloTrack** | Folder listing 2026-09-07; `26*/OUTCOME_CONTRACT.md` line 10 declares Type D, opened 2026-08-20 |
| Is P26 finished? | **Yes** — `07_Published_GitHub/`, `09_Closure/`, `RUN_THIS_TO_PUBLISH.md` and four publish scripts all exist | folder listing |
| Does its folder name match its contents? | Yes | folder listing |
| Is it in the cost ledger? | Yes — 11 sessions, 16.9 h, marked **PARTIAL (compaction)** in 8 of 11 | `_ENGINE/reference/PROJECT_COST_LEDGER.md` |

---

## 1. Scope and architecture

| | P26 VeloTrack | P27 PalmDesk |
|---|---|---|
| Domain | Live logistics / fleet telemetry | Commodity trading & risk (CTRM), palm oil |
| Data plane | Eventstream → **Lakehouse** (Bronze) → Materialized Lake Views (Silver/Gold) | **Warehouse** + T-SQL engines, batch EOD |
| Direct Lake source | **Lakehouse `LH_VeloTrack`** (Gold) | **Warehouse `WH_PalmDesk`** |
| Semantic model | ~20 measures, authored via XMLA/TMDL | 82 measures, 3 calculation groups, TMDL via Core MCP |
| Report | 4 pages | 4 pages, 56 visuals |
| Sessions | 11 (8 partial) | **3, none partial** |
| Published | Yes | No — publishing is the hand-off |

---

## 2. The comparison that matters: why the Direct Lake assumption survived so long

This is the single most useful output of comparing against the *right* project.

| Project | Direct Lake source | OneLake connector correct there? |
|---|---|---|
| 24 GlobalEnergy | Lakehouse | **Yes** |
| 26 VeloTrack | **Lakehouse** (`LH_VeloTrack` Gold) | **Yes** |
| 27 PalmDesk | **Warehouse** | **No** — needs `Sql.Database` |

The engine did not carry a *guess* forward. It carried a shape that had been **correct twice, in two
separate delivered projects**, and every repetition made it look more settled. P27 is the first time
the engine pointed Direct Lake at a Warehouse, and the first time the shape was wrong.

**That reframes the lesson.** It is not "we were careless once". It is: **a shape's proof is scoped
to the source it was proven against, and repeated success against the same source type is not
additional evidence for a different one.** Two confirmations of a Lakehouse binding say nothing about
a Warehouse binding, but they feel like they do.

---

## 3. What was reused, and what that reuse cost

**Reused and right:** PBIR visual shapes (each citing a delivered sibling), the component library,
the theme rule, `validate_pbip.py`, the cost-capture tool, the `.pbip` layout, and **P24's
calculation-group TMDL shape** — grepped, not remembered, and correct first time.

**Reused and wrong:** the Direct Lake connector, per §2.

**Reused and nearly wrong:** measure-level `isHidden`. S3 needed it for the 32 altText measures and
did **not** write it from memory — a corpus scan of 456 `.tmdl` files found 4 delivered instances
(Projects 16 and 19). Had that scan come back empty, the shape would have been dropped rather than
guessed.

---

## 4. What P27 learned that P26's record does not reflect

1. **Direct Lake connector selection is source-dependent.** P26 could not have learned this; its
   source was a Lakehouse. Now a `SETTLED.md` row with a 2026-12-07 re-check.
2. **The Core MCP payload ceiling is reached by growth** (F-30, F-33) — see C5.
3. **A 502 from the DW MCP gateway is not a rollback** (F-2). P26's channel was not the DW MCP.
4. **Fabric artefact editors remain unactionable by browser automation** — now confirmed on a third
   surface, the Warehouse ribbon.
5. **Replay determinism has a cheap proof:** re-run a bounded idempotent slice and compare frozen
   control totals. 3 DW MCP calls instead of a 120-day re-run.

## 5. Numbers of P26's that P27 can extend

- **Session hygiene.** P26 ran **11 sessions, 8 of them PARTIAL (compaction)** — its cost record is
  therefore a floor, not a total. P27 ran **3 sessions, 0 partial, 0 compaction boundaries**, so
  P27's figures are totals. Fewer, denser sessions produced a *more* trustworthy cost record, not
  merely a cheaper one.
- **`cr/turn`.** P26: 220,498 (but partial, so understated). P27: **427,129** — and **not** falling:
  432,257 → 398,987 → **458,855**. See C8 §3, which had to correct itself once the mandated close
  re-capture landed: the close ritual is the most expensive part of a session per turn.
