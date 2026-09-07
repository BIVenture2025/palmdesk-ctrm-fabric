# C5 — What to do better next project — Project 27

**Diagnose before prescribing.** Each item below establishes a cause from evidence before proposing
a fix.

---

## 1. What I did wrong

### 1.1 Carried a Direct Lake connector across a change of source type without re-probing — the project's largest single cost

*Evidence:* `FINDINGS_S2.md` F-29; C3 §2 shows the shape was correct in P24 and P26, both Lakehouse.
*Cost:* roughly half of Session 2 (of 4.2 h) plus the opening of Session 3.
*Cause, precisely:* not "reuse without checking" — a delivered sibling **was** consulted. The failure
is that **source type was not treated as part of the shape's identity**. Two prior confirmations
against a Lakehouse felt like evidence about a Warehouse; they were not.
*Why nothing caught it:* the wrong form is a *legal* datasource kind. It validates on create, loads
metadata, draws all twelve tables in the modelling canvas, and passes `validate_pbip.py` and the PBIR
schema validator. **Only a rendered value checked against a number computed elsewhere can see it.**

### 1.2 Hand-wrote the `.pbip` `$schema` from memory (F-31)

*Evidence:* guide §153; Desktop rejected the file; 23 delivered `.pbip` files had it right.
*Cause:* it was generated in a one-off heredoc rather than by the generator, so it escaped review.
*Already fixed in S3:* `build_report.py` now owns **both** packages — the `.pbip` and the publish
package — for exactly this reason, and three `validate_pbip.py` rules lint it.

### 1.3 Shipped a calculation item whose grand total was meaningless, and nearly verified it as correct

*Evidence:* S3, `Time Calculation Group` → `Day over Day`. As first written it compared
`SELECTEDMEASURE()` **in the whole filter context** against a single prior day, so at a grand total it
differenced 120 days against one.
*How it was caught:* the Warehouse truth was computed **before** the render was read. Had the render
been read first, "15,581,829" would have looked entirely plausible.
*Fix applied:* added an explicit `Current Day` item so `Day over Day` has a self-consistent left-hand
side; re-pushed and re-verified.
*Generalisable rule:* **compute the expected value before looking at the artefact, every time.** This
is §132 in its sharpest form and it earned its keep twice in one session.

### 1.4 Let the semantic model grow past its only deployment channel without watching the number

*Evidence:* F-33. Model array JSON went 55,333 (S2, deployable) → 60,480 (S3 calc groups, deployable)
→ 69,736 (S3 + 32 altText measures, **could not be emitted**).
*Cause:* F-30's planning rule — *budget ≤ ~50 KB per item push and size the deliverable to it at
Phase 0* — was applied to the **report** at Phase 0 and never applied to the **model**, because the
model started comfortably inside the ceiling.
*Consequence:* the 32 altText measures exist on disk and in both `.pbip` packages but **not in the
live model**, so the service report cannot resolve them until a Desktop publish carries the model up.

---

## 2. What the user did that cost time

**One item, and it is the same one as S2's.**

The **SQL connection string** was the single input that unblocked the Direct Lake binding, and no
session channel exposes it — `SERVERPROPERTY('ServerName')` returns only the workspace GUID, and the
"Copy SQL connection string" affordance is absent from the DOM menu. It was supplied on 2026-09-07,
after the blocker had already consumed most of S2.

**This is stated as a channel gap, not as a fault.** The value was not withheld; it was never asked
for as a *specific value* until S2's Addendum 3 worked out that it mattered. The lesson belongs to the
engine: **when a component's binding cannot be established from inside a session, name the exact
value needed and ask for it in the first batched ask, not the fourth.**

**What the user did that was right and I did not:** the **model-view screenshot** (S2 Addendum 2) and
the **DAX query view error** (Addendum 3). Those two reads did what four rounds of my own probing
could not — the first proved the model was not empty, the second proved the *tables* did not load and
cleared all 50 measures at once. I had been treating the per-table warning triangles as the
diagnosis; they are generic Direct Lake boilerplate. The user's reads were better-chosen than mine.

---

## 3. Changes ranked by expected value

| # | Change | Evidence | Cost to adopt | Expected value |
|---|---|---|---|---|
| 1 | **Probe a Direct Lake binding with a two-table model before building on it, whenever the SOURCE TYPE differs from the last proven one.** Record source type alongside every reusable shape | F-29; C3 §2 | ~10 min per new source type | **Highest.** Would have saved ~1 session here, and the same trap is waiting for the first mirrored-database binding |
| 2 | **Extend the Phase-0 payload budget to every item that will be pushed, and re-measure it at each session close** — not just the one artefact known to be large | F-33; the 55 → 60 → 70 KB progression | One line in the close ritual; ideally a `validate_pbip.py` lint that prints array-JSON size per pushable item | **High.** Turns a hard stop into a number you watch go up |
| 3 | **Compute expected values before reading any render.** Make it the stated order in the §132 gate, not an implicit habit | §1.3 above; F-29's own table | Zero — it is a reordering | **High.** Caught a real defect in S3 at no cost |
| 4 | **Fix the stale `CLAUDE.md` Type D list** (omits Project 26) and add a check that the list is derived, not hand-maintained | C3 §0 | Minutes; `weekly_scan.py` could derive it from `OUTCOME_CONTRACT.md` line 10 across `Projects/` | **Medium-high.** It sent this very closure to the wrong comparable on the first pass |
| 5 | **When a shape is grepped from a sibling, record what it was proven against**, not just where it came from | C6 | A comment convention in the generators | **Medium.** Makes #1 mechanical rather than remembered |
| 6 | **Ask for un-derivable environment values in the first batched ask.** Maintain a short "values no session channel exposes" list per platform | §2 above | One section in Skill 8 Phase 0 | **Medium.** Directly addresses the only user-side cost this project had |
