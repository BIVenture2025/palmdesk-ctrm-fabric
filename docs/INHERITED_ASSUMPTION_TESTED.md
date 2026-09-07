# C6 — Test one assumption the project ran on — Project 27

## The assumption

> **"Grep a delivered sibling, never write a shape from memory."**
> — `CLAUDE.md` Standing Rules; guide §48a; restated in this project's own kickoff.

This is the single most load-bearing inherited rule in the engine: it governs TMDL, PBIR, `.pbip`
packaging, calculation groups, themes and connector expressions. Project 27 is an unusually good
place to test it, because the project **broke it once, followed it many times, and — most usefully —
followed it and was still wrong once.**

**Test it, do not defend it.**

---

## Method

Enumerate every *shape decision* in P27 whose provenance is recorded, classify each on two axes —
**provenance** (grepped from a delivered sibling / written from memory) and **outcome** (correct /
defective) — and read the contingency table.

A "shape decision" is a structural form emitted into an artefact: a visual's query shape, a TMDL
block form, a schema URL, a connector expression, a packaging layout.

---

## Results

| # | Shape | Provenance | Outcome |
|---|---|---|---|
| 1 | 7 PBIR visual types (`cardVisual`, `matrix`, `columnChart`, `lineChart`, `waterfallChart`, `textbox`, `pageNavigator`) | Grepped (P26, P07, P03 — each cited in `pbir.py`) | ✅ correct |
| 2 | Calculation-group TMDL block | Grepped (P24 `Scenario/Time Calculation Group.tmdl`) | ✅ correct first time |
| 3 | Measure-level `isHidden` | Grepped (corpus scan: 456 `.tmdl` read, 4 instances, P16 + P19) | ✅ correct |
| 4 | `general.altText` bound to a Measure | Grepped (P07 `ESGSegBar/visual.json`) | ✅ correct |
| 5 | Custom theme registration | Grepped (P16, cited in `pbir.py`) | ✅ correct |
| 6 | `.pbip` shortcut `$schema` | **Memory** (one-off heredoc) | ❌ **defective** (F-31) |
| 7 | Direct Lake connector expression | **Grepped** (P24) | ❌ **defective** (F-29) |
| 8 | `formatStringDefinition` on a calc item | Grepped — **no sibling found**, so *not written* | ✅ correct by omission |

| | Correct | Defective |
|---|---:|---:|
| **Grepped** | 6 | **1** |
| **From memory** | 0 | **1** |

---

## What the data actually says

**1. The rule holds for what it was written to prevent.** Every *syntactic* shape defect in this
project's history came from memory, and the one from-memory shape in P27 was defective. Zero grepped
shapes were syntactically wrong. Row 8 is the rule working in its strongest form: no sibling existed,
so nothing was written, and a plausible-looking guess never entered the artefact.

**2. The rule does not cover the failure that cost the most.** Row 7 is the important cell. The
connector was grepped from a delivered, working, validated sibling — and was still wrong, because the
sibling's **source type differed** (Lakehouse vs Warehouse). The rule protects against *inventing* a
shape. It says nothing about *transplanting* a correct shape into a context it was never proven in.

**3. Therefore the assumption is true but incomplete, and the amendment is precise:**

> Grep a delivered sibling, never write a shape from memory — **and record what the sibling was
> proven against. A shape's proof is scoped to its source; repeated success against the same source
> type is not evidence for a different one.**

---

## Confounds, stated

- **Survivorship bias, and it is large.** Only shape decisions that were *recorded* can be counted.
  Shapes grepped and silently correct are systematically undercounted, which biases the table in the
  rule's favour. The true "grepped & correct" count is certainly higher than 6 — which strengthens
  conclusion 1 and leaves conclusion 2 untouched, since it rests on a single well-documented cell.
- **n = 8 is small**, and one project cannot settle a corpus-wide rule.
- **Outcome classification is not blind** — it was done by the same agent that made the decisions.
- **The two defects are not independent of the finding process**: both were found *because* they broke
  loudly. A grepped shape that is subtly wrong and never renders visibly would appear in neither
  column. This is the same blind spot F-29 itself exposed.

## Verdict

**The assumption survives, with a necessary amendment.** It is not defended: the data shows one
grepped shape that was wrong, and the reason it was wrong is not covered by the rule as written. The
amendment in §3 is dual-written to the guide and folded into `CORE_RULES`, and the source-type probe
it implies is C5's #1 recommendation.
