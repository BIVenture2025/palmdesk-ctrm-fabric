# C8 — Cost analysis and the ledger row — Project 27

Source: `capture_session_cost.py --merge _cost`, run 2026-09-07. **Three snapshots, none `partial`,
zero compaction boundaries** — so these are totals, not floors. That is the first fully complete cost
record in the ledger.

---

## 1. Ledger row (appended to `_ENGINE/reference/PROJECT_COST_LEDGER.md`)

| Project | Sessions | Active h | Turns | Tool calls | Browser % | Cache read | Output | cr/turn |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 27 PalmDesk | 3 | 9.5 | 1,400 | 868 | 19% | 597,980,316 | 2,284,489 | 427,129 |

**No caveat flags.** Compare the neighbours: P24 `INCOMPLETE` (14 sessions missing), P25 `INCOMPLETE`
+ `PARTIAL`, P26 `PARTIAL` in 8 of 11. P27's row is the only one that can be quoted without a
qualifier.

---

## 2. Per session

| S | Phase | Turns | Active h | Cache read | **cr/turn** | Tool calls | Browser % |
|---|---|---:|---:|---:|---:|---:|---:|
| 1 | Gates, scaffold, data plane | 558 | 3.2 | 241,199,284 | 432,257 | — | 19% |
| 2 | Model, report, alerts | 494 | 4.2 | 197,099,499 | 398,987 | — | 26% |
| 3 | Resolve, verify, replay, close | 348 | 2.0 | 159,681,533 | **458,855** | 200 | 10% |
| | **Project** | **1,400** | **9.5** | **597,980,316** | **427,129** | **868** | **19%** |

Output 2,284,489 · cache-write 12,662,991 (**12.5× a read**, the usual ratio).

**Subagents, reported separately and not netted in:** 10 transcripts across S1 and S2 —
66,894,783 cache-read and 268,072 output. Real spend on the same task. S3 used **no subagents**.

---

## 3. `cr/turn` — the quantity that tests session hygiene, and the correction this section had to make

The split-session hypothesis predicts `cr/turn` stays **flat** across sessions rather than growing; a
rising column falsifies it.

**432,257 → 398,987 → 466,494. It is not flat. Session 3 is the highest of the three.**

*(Three captures of S3 exist and each is higher than the last: 398,183 at 06:25:29Z, 458,855 at
06:40:37Z, **466,494 at 06:42:15Z — the committed one**. The per-session table above quotes the
06:40:37Z capture because the project merge was run against it; `_cost/session-03.json` is the
authority and reads 466,494 over 359 turns. The three figures are not an error — they are the
measurement of the effect this section is about.)*

**This section originally said the opposite, and the reason is worth more than the number.** The
mid-session checkpoint taken at 06:25:29Z read **398,183** — flat-to-falling, and a tidy result. The
mandated close re-capture at 06:40:37Z, taken *after* the handover as §113/§125 requires, read
**458,855**. Fifteen minutes of writing moved the figure by 15%.

**What that says, and it is a real finding:** the **close ritual is the most expensive part of a
session per turn**. It runs at maximum context depth, and it is output-heavy — C1 through C8, the
handover and the publishing hand-off were all written after the checkpoint. **Measuring `cr/turn`
before the close systematically understates it**, and any session that captures its cost snapshot
early will report a flattering number. This project's own S1 and S2 figures were captured the same
way, so the whole column is probably understated by a similar margin — which means the comparison
across sessions is fair even though each level is low.

**Verdict, stated honestly:** P27's data **does not support** the flat-`cr/turn` prediction. Whether
that falsifies the hypothesis is a different question and this project cannot settle it, because the
three sessions did different kinds of work — S1 built, S2 diagnosed, S3 verified *and closed*. The
closure load falls entirely on S3 and is not a hygiene failure; it is the shape of a final session.

The level (427,129) remains high against P25 (252,770) and P26 (220,498, understated because
partial), and below Project 23's single-session benchmark of 478,216.

## 4. Browser share — 20%, over the engine's cap, and reported not optimised

Per guide §148 the Type-D browser metric is a **safety and reviewability ceiling, not a cost target**.
The 20% has one structural cause and one avoidable component.

**Structural (most of it):** Fabric's artefact editors are canvas-drawn and unreachable by any API
this tenant has, and the §132 render gate can only be satisfied by reading a rendered page. S3 read
renders three times — the calculation-group verification page and all four report pages.

**Avoidable (small):** S3 spent several calls fighting a browser window that would not resize past a
173 px viewport, trying to read matrix values from pixels. The fix, found late, was that **Power BI
matrix visuals are DOM, not canvas** — one `javascript_tool` read returned every value as text, and
the engine's own standing rule already says *anything a query returns is pasted as text, never a
screenshot* (guide §120). Roughly 6 browser calls wasted. **Recommendation: read Power BI report
values from the DOM first; use a screenshot only when layout itself is the question.**

S3's browser share (**10%**) is the lowest of the three sessions despite carrying the whole render gate — the DOM-read fix in F-35 arrived mid-session and the remaining browser calls were front-loaded.

---

## 5. What the money bought, per session

| S | Cache read | Delivered |
|---|---:|---|
| 1 | 241M | Warehouse, 16 tables, 5,919 rows, 5 procedures, 120 days, 39 control totals frozen |
| 2 | 197M | Model + 4-page report on disk; **and the connector root cause** — half of it a negative result that was nonetheless the project's most valuable output |
| 3 | 160M | 3 calculation groups verified live, altText 32/32, §132 gate closed on all 4 pages, replay proven deterministic, closure |

S3 delivered the most verified outcomes for the least spend — the expected shape when a session
starts from a solved blocker rather than an open one.

---

## Addendum — what the post-close verification cost, and the correction it forces on §3

Session 3 did not end at its close. The operator reported a republish; it was verified rather than
accepted; it had not landed; and **134 further turns** went into diagnosis, measurement and
dual-writing (F-40, F-41, F-42).

| Measure | Close snapshot 06:42:15Z | Addendum 07:19:27Z | Basis |
|---|---:|---:|---|
| Turns | 359 | **≥493** | `capture_session_cost.py` |
| Cache read | 167,471,187 | **≥203,102,434** | ditto |
| Output | 875,064 | **≥1,028,449** | ditto |
| cr/turn | 466,494 | **≈411,972** | derived |
| Compaction boundaries | **0 — complete** | **1 — `truncated: true`** | the snapshot's own field |

**Every addendum figure is a floor, not a total.** The close snapshot is the only boundary-free
measure of this session and is kept beside the addendum rather than replaced by it. Reporting the
07:19 numbers as totals would be exactly the §104 failure this project keeps finding elsewhere.

### The correction to §3

§3 concluded that **the close ritual is the most expensive part of a session per turn** — 398,183
cr/turn at the 06:25 checkpoint against 466,494 at close. That direction still holds within a single
context. But the 134 post-close turns ran at roughly **267k cache read per turn implied**, well below
the session's 466k average, while doing some of the session's most careful work.

**So the driver is context length, not the nature of the work.** A compaction resets what each turn
has to carry, and cost per turn falls with it. The refined statement:

> Closing is expensive because it happens at the end of a long context, not because closing is
> intrinsically costly. **The cheapest place to do careful verification is immediately after a
> compaction** — and the most expensive is the last hour before one.

**Practical consequence for the next Type D project:** if a session's close is going to involve real
verification rather than paperwork, it is cheaper to compact first and then verify. P27 got that
ordering by accident and paid roughly 43% less per turn for its three best findings.
