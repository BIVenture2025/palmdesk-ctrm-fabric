# C1 — Stage-by-stage post-mortem — Project 27, Fabric E2E CTRM Analytics Layer (PalmDesk)

**House rule for this document: every number states its basis. Where a thing could not be measured,
it says so and says what it was inferred from.**

Closed 2026-09-07. Type D (platform estate). Three sessions, all on `claude-opus-5`.

---

## 1. Per-phase table

| S | Planned | Actual | Hiccup | Learning | Pivot | Cost (basis: `_cost/session-0N.json`) |
|---|---|---|---|---|---|---|
| 1 | Phase 0 gates + scaffold + data plane | Delivered: Warehouse, 16 source tables, 5,919 rows, 5 procedures, 120 business days run, 39 control totals frozen 09:49:22Z | Four T-SQL shapes rejected in distributed mode; two 502s from the DW MCP gateway | **F-2** a 502 is not a rollback — the gateway drops the call at ≈100 s while the Warehouse keeps executing; **F-3** the four rejected shapes | Gate 7 (SQL database as OLTP store) **killed in the session it failed** | 558 turns · 3.2 h · 241,199,284 cache-read · 432,257 cr/turn · browser 19% |
| 2 | Phase 2 model, report, alerts | Model + 4-page report built and validated on disk; **every bound visual returned `Missing_References`** | The Direct Lake blocker — consumed roughly the first half of the session | **F-29** a Fabric **Warehouse** binds through Direct Lake **on SQL**, not on OneLake | Contract fallback (`.pbip`) executed in the session the gate failed; five hypotheses eliminated by controlled probe | 494 turns · 4.2 h · 197,099,499 cache-read · 398,987 cr/turn · browser 26% |
| 3 | Phase 3 resolve, verify, replay, close | 3 calculation groups live and verified; altText 32/32; **§132 gate completed on all four pages**; replay proven deterministic; probes removed; closure | **F-33** the model outgrew the only deploy channel this tenant has | **F-33** Core MCP payload ceiling is reached by *growth*, not by one big artefact | altText deployed to disk only; the service model keeps the 50 base measures | 267 turns · 1.7 h · 106,314,924 cache-read · 398,183 cr/turn · browser 14% |

---

## 2. Every count this project asserts, enumerated

Skill 10's highest-yield rule: *if the project asserts a count of anything, enumerate it here.*
Each row below was **re-derived mechanically on 2026-09-07**, not copied from a handover.

| Asserted | Value | How it was established (command / query) |
|---|---:|---|
| Model tables | **15** | `ls 04_Model/.../definition/tables/*.tmdl` — 12 Direct Lake + 3 calculation groups |
| Direct Lake tables | **12** | same scan, excluding tables carrying `calculationGroup` |
| Calculation groups | **3** | tables matching `^\tcalculationGroup` |
| Calculation items | **15** | `^\t\tcalculationItem` — 6 Bucket + 7 Time + 2 Currency |
| Direct Lake columns | **108** | `^\tcolumn` across the 12 Direct Lake tables only |
| Measures | **82** | `^\tmeasure` — **50 base + 32 altText**. S2's handover said "50 measures"; that was true at S2 and is now superseded |
| Relationships | **13** | `^relationship ` in `relationships.tmdl` |
| Report pages | **4** | `definition/pages/*/page.json` |
| Report visuals | **56** | `definition/pages/*/visuals/*/visual.json` |
| Data-bearing visuals | **32** | of the 56, those carrying `visual.query` |
| altText coverage | **32 / 32** | `validate_pbip.py` — the deliverable no longer appears in the `ALTTEXT_COVERAGE` warning list |
| Control totals | **39** | `SELECT … FROM eng.control_total` — 39 rows, twice (pre- and post-replay) |
| Workspace items at close | **9** | `list_items` unfiltered, 06:20:01Z |
| Source rows loaded | **5,919** | S1, verified then by COUNT + checksum against `01_Source/out/manifest.json`. **Not re-derived in S3** — inferred from S1's evidence and from the 39 unchanged `SOURCE_ROWS` control totals, which sum to 5,919 |
| Business days | **120** | `COUNT(*) FROM ref.calendar` = 120; `eng.run_log` = 120 |
| Sessions | **3** | `_cost/` holds three snapshots, none `partial` |

**One correction to the record.** S2's handover and the Rev 3 contract both say the model carries
"50 measures". After S3 that is **82**. The 50 figure was correct when written; it is restated here
so a later reader does not treat it as a live count.

---

## 3. Cross-phase patterns the per-phase table cannot show

**Pattern 1 — the project's single largest cost was one inherited assumption, never re-probed.**
Every Direct Lake model this engine had built used the OneLake connector, proven once on a
**Lakehouse** in Project 24 and then copied onto a **Warehouse**. It validates on create, loads its
metadata, draws all twelve tables with their relationships in the modelling canvas, and passes
`validate_pbip.py` and the PBIR schema validator. It simply never binds a table. Cost: most of two
sessions. A two-table probe would have caught it in ten minutes on day one.

**Pattern 2 — three of the three genuinely novel findings came from a rendered value, not a
validator.** F-29 (wrong connector), F-31 (wrong `.pbip` `$schema`) and the S3 `Day over Day`
defect were all invisible to every structural check the engine owns. F-31 was caught only because a
human opened the file; the `Day over Day` defect was caught only because the Warehouse truth was
computed **before** the render was read.

**Pattern 3 — the two ceilings this project hit were both about what an agent can *emit*, not what
the API accepts.** F-30 (≈83 KB array JSON could not be emitted) and F-33 (≈70 KB could not be
emitted, ~60 KB could) are the same wall measured twice, and both were reached by a deliverable
growing, not by a single oversized artefact.

**Pattern 4 — no defect planted in one phase detonated in a later one.** This is the opposite of
Project 24's headline pattern (six of eleven phases planted a defect that detonated ~3 phases later),
and the plausible reason is the contract's kill criteria: two components (SQL database, mirror) were
killed in the session they failed rather than carried.

---

## Addendum — 2026-09-07 07:20: the publish was checked, not assumed

The operator reported the PBIP saved and republished. Verifying it rather than accepting it is the
single most productive thing done in this session, and it produced three findings (F-40, F-41, F-42)
that are worth more than the deliverable they failed to ship.

**What was wrong:** the folder opened was `P27_PalmDesk_publish/` — the **byConnection** package,
which carries no model. The report went up; the model did not. The 32 altText measures are still
absent from the tenant. **The live model carries 50 measures, not 82.**

**Why it would have gone unnoticed:** Power BI silently drops an altText binding to a missing
measure. The republished report renders 28 containers, 0 errors, every figure matching Warehouse
truth. It is pixel-identical to a correct build. **This is the project's central lesson arriving a
second time on a different surface** — first the Direct Lake connector, now a formatting property:
*a clean-looking render of a broken model is indistinguishable from a correct one unless the value
came from somewhere else.* The instrument that settled it was an `AltProof` card binding the alt
measures as **visible** values, deliberately left in place and failing as a live regression test.

**What the naming defect cost:** the hand-off named the correct folder (`P27_PalmDesk_pbip/`). The
folder that was opened was the one called `_publish`. **That is an engine defect, not an operator
error** — a directory name that points away from its own binding. Logged as F-41 with the standing
rule to name packages `*_byConnection` / `*_byPath`.

**Honest accounting of the two automated escapes**, both measured rather than estimated: the Core
MCP payload is 69,186 with the alt measures against a 60,490 known-good, and every safe reclamation
combined still lands at 63,330 — the channel genuinely cannot carry them. XMLA/TOM *can*, and the
channel is proven to exist, but its re-auth cannot complete inside the device bridge's 60-second
ceiling. **The one durable takeaway for the next Type D project: have the operator sign the XMLA
connection in on the machine before the session starts, and the emit ceiling stops being a blocker.**

### Closed 08:20 — and the second attempt cost one page load

The byPath publish landed with the overwrite accepted. `AltProof` renders three correct sentences,
the breach count is confirmed against the Warehouse independently (4 of 40 at 2026-08-28), the scan
that failed at 07:05 passes on the deliverable, and the workspace still reconciles to 9 items with
`SM_PalmDesk` unchanged — **no duplicate dataset.** The live model carries all 82 measures.

**The point worth carrying out of this project:** the first publish failed silently and cost an hour
of inference to disprove. The second was confirmed in **one page load**, because by then an
instrument existed that could only be green if the thing were true. Building the check cost about
ten minutes and turned an unanswerable question into a glance.

> **Where a property has no visible output, the deliverable is not done until something exists that
> fails when it is wrong.**

Two smaller things fell out of the second attempt. Publishing straight from open to Publish, without
saving, left the byPath package's pinned `visualContainer` 2.11.0 untouched at 56/56 — **Desktop
rewrites on save, not on publish** (F-43 mitigated). And the overwrite risk flagged in the hand-off
did not materialise: it replaced in place rather than landing as a new dataset. Both were flagged as
unknowns rather than guessed at, and both resolved in the deliverable's favour.
