# FINDINGS — Session 3 (Phase 3: resolve, verify, replay, close), 2026-09-07

Numbering continues from S2 (F-15…F-32). Each finding names the call that established it.

---

## F-33 — The Core MCP ceiling is reached by GROWTH, and the binding limit is the agent's own emit budget → CHANNELS, SETTLED (extends F-30)

F-30 bracketed the ceiling with three sized pushes of *different artefacts*. S3 pushed **the same
artefact four times as it grew**, which is the shape the ceiling is actually met in:

| Push | Content | Parts | Array JSON | Result |
|---|---|---:|---:|---|
| S2 final | 12 tables, 50 measures | 17 | 55,333 | ✅ |
| S3 #1 | + 3 calculation groups | 20 | **60,036** | ✅ LRO `5c4247a8-…`, 3.0 s |
| S3 #2 | + `Current Day` calc item | 20 | **60,480** | ✅ LRO `87677be8-…`, 1.8 s |
| S3 #3 | + 32 altText measures | 20 | **69,736** | ❌ **could not be emitted** |
| — | same, `///` descriptions stripped | 20 | 64,772 | not attempted |
| — | same, descriptions stripped + narrations shortened | 20 | 64,208 | not attempted |

**The bracket is now 60,480 ✅ / 69,736 ❌**, tighter than F-30's 55,333 ✅ / 82,646 ❌.

**Three things this adds to F-30:**

1. **The wall is the agent's output budget for one tool call, not the API.** F-30 already said the
   request "is never issued". S3 confirms it from the other side: the 69,736 attempt failed while
   *emitting*, with no request and no error from Fabric.
2. **Compaction is not a lever once it has been spent.** The report's deployment twin was already
   compacted in S2 (raw 56,980 B vs 119,646 B readable) and still measured 82,646. On the model,
   stripping all `///` descriptions bought only 4,964 chars (7%) and shortening 14 narrations bought
   564 more. **Budget the ceiling; do not plan to compress into it.**
3. **The failure mode is a deliverable growing across sessions**, not one oversized artefact. F-30's
   planning rule was applied to the report at Phase 0 and never to the model, because the model
   started comfortably inside the ceiling. It ended outside it.

**Consequence for P27, stated plainly:** the 32 altText measures are in the on-disk model and in both
`.pbip` packages but **not in the live `SM_PalmDesk`**. Fabric REST / `fab` / `az` / OneLake are all
unreachable from either shell (SETTLED), so Core MCP is the only push channel. Per contract §4 the
next channel down was taken: **generate offline, user publishes** — from
`06_Report/P27_PalmDesk_pbip/` (byPath), which carries the model and the report together.

**Planning rule (supersedes F-30's, extends it):** budget array JSON **≤ ~50 KB per pushable item**,
and **re-measure every pushable item at every session close**, because the number moves as the
deliverable grows. A `validate_pbip.py` lint that prints array-JSON size per pushable item would make
this mechanical.

---

## F-34 — The `device_bash` result cap bites BEFORE the emit ceiling, and it is a different wall → CHANNELS

Printing the 20-part model payload for re-emission failed at **59,035 characters** with
*"result … exceeds maximum allowed tokens"*, before the emit ceiling was reached. The output was
written to a container-side file instead, and had to be read back in four chunks.

Two distinct limits, easily confused, on the same workflow:

| Wall | Measured | Direction |
|---|---:|---|
| `device_bash` tool result | ≈ 59 KB | reading a payload OUT of the device |
| Core MCP emit (F-33) | 60,480 ✅ / 69,736 ❌ | writing a payload INTO the tenant |

**Rule:** when a payload must cross from the device to a tenant push, print it in chunks sized to the
*result* cap, not to the push ceiling — or keep the artefact small enough that neither binds.

---

## F-35 — Power BI report values are DOM, not canvas: read them as text → GUIDE (this is guide §120 applied to renders)

S3 spent roughly six browser calls trying to read matrix values from pixels, fighting a Chrome window
that would not resize past a 173 px viewport (`resize_window` reported success; the frame stayed
173 px, and `zoom` regions drifted between calls).

**The whole problem was self-inflicted.** Power BI matrix and card visuals render into the DOM. One
`javascript_tool` read returned every value as text, exactly and instantly — including the cell that
settled the USD question, whose `title` attribute carried the formatted value.

This is the engine's own standing rule, already written for query results and never applied to
renders: **anything that can be returned as text is pasted as text, never read from a screenshot.**
A screenshot is for when the *layout itself* is the question — spacing, overlap, a malformed axis.

**Consequence:** the §132 pixel gate is better satisfied by a DOM read of the values plus a single
screenshot for layout, than by squinting at pixels. It is faster, exact, and it lowers the browser
share the Type-D metric caps.

---

## F-36 — `CLAUDE.md`'s Type D project list is stale, and the C3 discipline caught it → ENGINE FIX

`CLAUDE.md` Project Type Fork: *"Type D so far: 23 (Nordhaus O2C) · 24 (GlobalEnergy FP&A) ·
25 (Meridian Pay RTI)."* It **omits Project 26**, whose `OUTCOME_CONTRACT.md` line 10 reads
*"Type D (platform build) · opened 2026-08-20"*.

Found only because Skill 10 C3 says *do not trust the CLAUDE.md row*. The closure's comparison
document was **first drafted against Project 25 on the strength of that row, then rewritten against
Project 26** once the row was checked — and the rewrite produced the single most useful insight in
the closure (C3 §2: the Direct Lake assumption survived because P24 *and* P26 were both Lakehouse).

**Fix:** correct the list, and stop hand-maintaining it — `weekly_scan.py` can derive it by grepping
`Type D` in each `Projects/*/OUTCOME_CONTRACT.md`.

---

## F-37 — `scrub_check.py` reports a verdict without reporting how much it read → ENGINE FIX (App C 24)

`scrub_check.py 09_Closure` printed `CLEAN -- no credentials, endpoints or tenant identifiers found.`
and `--json` printed `[]`. **Neither says how many files or bytes were scanned**, so "clean" and
"scanned nothing" are indistinguishable — precisely the failure App C 24–25 and guide §124 exist to
prevent, in a tool the engine trusts to gate exports.

Verified independently this session: 9 files in scope, and `grep -rl` for the SQL endpoint returned
nothing. **Fix:** add a `[scan] N file(s), M bytes read` line, and make a zero-file scan a failure.

---

## F-38 — A calculation item can be structurally perfect and semantically meaningless at the grand total → GUIDE

The `Time Calculation Group`'s `Day over Day` item, as first written, computed
`SELECTEDMEASURE()` in the **whole filter context** minus a single prior day. With one day in
context it is correct; at a grand total it differenced 120 days against one, yielding
15,581,829 — a number that looks entirely plausible.

Nothing structural could see it: `validate_pbip.py` passed 19 tmdl with 0 errors, and the TMDL shape
was grepped from a delivered sibling.

**It was caught only because the Warehouse truth was computed BEFORE the render was read.** The
expected values were derived in T-SQL first, and the render was then checked against them.

**Fix applied:** an explicit `Current Day` item now pins the left-hand side, so `Day over Day` is
self-consistent at any grain. **Rule:** for any measure whose value depends on the grain it is
evaluated at, state the expected value at *grand total* as well as at leaf level before reading a
render.

---

## F-39 — Replay determinism has a cheap proof → GUIDE

Proving a 120-day replay reproducible does not require re-running 120 days. The documented
restatement slice is idempotent per day, so:

1. snapshot the 39 frozen control totals;
2. re-run the 4-day restatement + `usp_hedge_tests` + `usp_freeze_controls` (**3 DW MCP calls**);
3. compare.

**Result: 39/39 control totals identical in value; only `frozen_at` moved (2026-09-06 09:49:22 →
2026-09-07 06:23:36).** Row counts unchanged, residual 0 on 120/120 days, and — the check that
nearly got missed — `eng.attribution_bucket_daily` (a separately materialised CTAS the replay does
**not** rewrite) still reconciles to the re-derived `attribution_daily` on **120 of 120 days, worst
absolute difference 0.000000**.

**The right signature for a determinism test is: the numbers do not move, the timestamps do.**

---

# Addendum — post-republish verification (2026-09-07 07:05–07:20)

Written after the operator reported "i have saved a version for PBIP and republish it". The claim
was **verified rather than accepted**, and it did not hold. Everything below is measured.

## F-40 — `general.altText` bound to a missing measure degrades SILENTLY → SETTLED

The main report `P27_PalmDesk` was republished at 06:55 and renders **28 containers, 0 error
visuals**. Every number on the Position page still matches Warehouse truth (MYR −168,330 MTM,
449 open positions, 84,270 MT net short). Nothing on the surface says anything is wrong.

But the 32 altText measures the report binds to **do not exist in the live model**. Power BI does
not error a visual whose `general.altText` points at a missing measure — it drops the property and
renders normally.

**This is the F-29 trap in a new place: a clean render is not evidence.** A report with 32 broken
altText bindings and a report with 32 working ones are pixel-identical. `ALTTEXT_COVERAGE 32/32`
passing on disk says nothing about the tenant.

**The instrument that works** is to bind the alt measures as *visible values* somewhere and see
whether the visual resolves them. An `AltProof` card was added to `RPT_PalmDesk_Check`'s
`CalcGroups` page for exactly this; it fails loudly and names the missing fields:

> Something's wrong with one or more fields or you don't have required permissions:
> (MTM Daily) MTM alt text, (MTM Daily) Open Positions alt text, (Exposure Daily) Breach count alt text

**The card is deliberately left in place and left failing.** It is the live regression test for this
question. When it renders three sentences instead of an error, the alt measures are live.

## F-41 — The `.pbip` byConnection / byPath trap: a report-only package cannot ship a model → CHANNELS, SETTLED

Filesystem evidence of what was actually opened (mtimes, this device):

| Package | Kind | Newest file | `.pbi/localSettings.json` rewritten |
|---|---|---|---|
| `06_Report/P27_PalmDesk_publish/` | **byConnection** (report only) | 2026-09-07 **06:55** | **yes** — Desktop opened it |
| `06_Report/P27_PalmDesk_pbip/` | **byPath** (carries the model) | 2026-09-07 06:14 (my build) | no — never opened |

The operator opened and republished the **byConnection** package. That package contains no
`SemanticModel` folder at all: it binds to the live model by connection. Publishing it pushes the
**report and nothing else**, which is precisely why the alt measures are still absent, and why
`list_items` still shows 9 items with unchanged GUIDs — the publish was real and it was correct for
what it was, it just had no model in it to send.

**The trap is that both packages are valid, both open in Desktop, both publish without complaint,
and only one of them can carry a model change.** The name `_publish` actively points the wrong way.

**Engine rule:** a package directory's name must state its binding. Rename on next use to
`*_pbip_byConnection` / `*_pbip_byPath`, and any hand-off instruction naming a publish folder must
say which of the two it is and what that folder can and cannot carry.

## F-42 — XMLA/TOM is a real fourth channel, but re-auth exceeds the device bridge's 60 s call ceiling → CHANNELS, SETTLED

Attempted as the next channel down after F-33's emit ceiling, per contract §4.

The local `powerbi-mcp-server` on the operator's machine exposes `ConnectFabric` +
`batch_measure_operations` (TOM over the workspace XMLA endpoint). This would bypass the emit
ceiling entirely: 32 measures could be created in batches of any size, because the payload never
has to be one agent utterance.

**The channel demonstrably exists.** `ListConnections` returns a real, previously established
connection:

```
Fabric-<WORKSPACE>-<MODEL>
connection string: XMLA endpoint powerbi://api.powerbi.com/v1.0/myorg/<WORKSPACE>, catalog <MODEL>
isCloudConnection: true   connectedAt: 2026-09-06T14:00:59Z          [values redacted per App C]
```

**What blocks it is the bridge, not the channel.** The cached token has expired, and every
`ConnectFabric` re-auth attempt returns `Device 'ywsbi' did not respond within 60s` — the
interactive MSAL sign-in cannot complete inside the remote-device bridge's fixed 60-second call
limit. Operating on the stale connection returns `Refreshing the expired access-token has failed`,
then `Object reference not set to an instance of an object` once the model handle is dropped.

**Settled shape: XMLA/TOM is usable from an agent session only while a token minted OUTSIDE that
session is still valid.** It cannot bootstrap its own authentication. To make it available, the
sign-in must be completed once on the device before the session needs it — after which batch model
edits of unbounded size are available for the token's lifetime.

**This is the most valuable channel finding of the project**, because it is the only known way past
the emit ceiling that does not require shrinking the artefact.

## F-33 CORRECTION — the bracket, measured reproducibly

F-33's table recorded the failing payload as 69,736 from the attempt itself. Rebuilding the model
from source and computing both payloads deterministically gives:

| Payload | Array JSON chars | Result |
|---|---:|---|
| Model **without** the 32 alt measures | **60,490** | ✅ this is what is live |
| Model **with** the 32 alt measures | **69,186** | ❌ cannot be emitted |

(69,186 vs the 69,736 recorded in the moment — a 550-char drift from intervening edits. The
reproducible figure is 69,186; both sit on the same side of the wall.)

**The 32 alt measures cost 6,524 raw chars — 8,696 of payload. The gap to the known-good is 8,696,
i.e. exactly the alt measures.** There is no slack.

Every safe reclamation was measured and none of them close it:

| Lever | Payload | Saves | Safe? |
|---|---:|---:|---|
| baseline with alt | 69,186 | — | — |
| drop `annotation SummarizationSetBy` | 68,242 | 944 | yes, inert |
| drop blank-line padding | 68,570 | 616 | yes, inert |
| drop column `sourceLineageTag` | 64,878 | 4,308 | **no** — protected Direct Lake diagnostic |
| all three combined | **63,330** | 5,856 | no |

**Even stripping everything, including the change the contract forbids reverting, lands at 63,330 —
still above the 60,490 known-good and inside the untested band.** F-33's conclusion is not just
upheld, it is now closed: the alt measures cannot reach the tenant through the Core MCP channel at
any safe compaction. The disk deliverable and one byPath publish are the only routes, and F-42 is
the only automated one.

## F-43 — A Desktop save silently upgrades pinned `visualContainer` schema versions, on half the visuals → SETTLED

Found by re-running `validate_pbip.py` after the republish: **7 warnings against a 6 baseline.** The
new one is `MIXED_VISUAL_SCHEMA_STACKS` on `P27_PalmDesk_publish/`.

| Package | visualContainer versions | Opened in Desktop? |
|---|---|---|
| `P27_PalmDesk.Report` (canonical) | **56 × 2.11.0** | no |
| `P27_PalmDesk_pbip/` (byPath) | **56 × 2.11.0** | no |
| `P27_PalmDesk_publish/` (byConnection) | **26 × 2.11.0 + 30 × 2.12.0** | **yes, 06:55** |

**Opening and saving the package in Desktop rewrote 30 of 56 visuals to a schema version this
project deliberately pinned at 2.11.0** — and left the other 26 alone, which is why it shows up as a
*mixed* stack rather than a clean version bump. The generator never emitted 2.12.0 anywhere.

**Three things follow.**

1. **A pinned schema version is only pinned until a human opens the file.** The engine pins versions
   at generation and validates them on disk; neither survives a round trip through Desktop. Any
   `.pbip` handed to an operator should be assumed to come back on a different schema stack.
2. **It is benign in the service, and that is measured, not assumed.** This mixed-stack package is
   the one that was actually published, and the live report renders 28 containers with 0 errors and
   every figure matching Warehouse truth. The warning is a consistency signal, not a defect.
3. **The baseline moves to 0 errors / 7 warnings.** `PUBLISHING_HANDOFF.md` §0.2 tells the next
   session to compare against 6 and to treat a *disappearing* warning as a moved snapshot. Left
   uncorrected, that instruction sends someone hunting a phantom. Corrected in place.

**Do not "fix" the package by regenerating it.** `build_report.py` would emit a clean 56 × 2.11.0
package, which would then differ from what is actually deployed. The mixed stack is the honest
record of what Desktop produced and what the tenant received.

## F-37 SHARPENED — the defect is on the CLEAN path only, and scope is the trap

F-37 said `scrub_check.py` reports a verdict without scan volume. Re-tested on both paths:

| Scope | Output |
|---|---|
| `09_Closure` (clean) | `CLEAN -- no credentials, endpoints or tenant identifiers found.` — **and nothing else. No file count, no byte count.** |
| project root (dirty) | `590 finding(s), 572 carrying a real value` + per-rule counts + per-file line numbers |

**So the tool is only blind when it says everything is fine** — the one verdict where a silent
zero-file scan and a real all-clear are indistinguishable, in a tool that gates exports. The fix
stands as filed: emit `[scan] N file(s), M bytes` on every path and fail a zero-file scan.

**The second half of this, which F-37 did not say: the verdict is meaningless without its scope.**
The same tool on the same project returns `CLEAN` and `DO NOT PUBLISH` depending only on the
directory argument, and **both are correct**. The project root legitimately carries tenant GUIDs,
SQL endpoints and workspace identifiers in its working documents; the closure folder legitimately
carries none. **Skill 9 must scrub the export it is about to publish, not the project root — and
must state which it scrubbed.** A `CLEAN` with no scope named is not evidence of anything.

*(Two `connection_string_kv` instances in this file were self-inflicted — the XMLA connection string
was pasted verbatim into F-42 while writing it up. Redacted to placeholders; the finding is
unchanged and the count is back to 0 instances. Worth recording because it is the exact failure mode
the rule exists to catch, committed by the person writing the finding about it.)*

---

# CLOSED 2026-09-07 08:20 — the byPath publish landed, verified on the instrument

The operator published from the byPath package and accepted the model overwrite. **The blocking item
is closed.** Verified three independent ways, none of them "the report looks fine":

**1. The `AltProof` card flipped from error to content.** The same card that read
*"Something's wrong with one or more fields: (MTM Daily) MTM alt text, …"* now renders:

> MTM alt text — Book mark-to-market at 2026-08-28: -168,330 MYR.
> Open Positions alt text — Open positions on the book: 449.
> Breach count alt text — Counterparties over their limit: 4.

**2. The values are right, not merely resolvable.** A narration measure that returns the wrong number
still renders a sentence. Checked against the Warehouse independently:
`SELECT SUM(CASE WHEN exposure > limit_myr THEN 1 ELSE 0 END) FROM eng.exposure_daily` at
`MAX(biz_date)` → **4 breaches of 40 counterparties at 2026-08-28**. Matches. MTM −168,330 and 449
open positions were already gated in the §132 pass.

**3. The exact scan that failed at 07:05 now passes on the deliverable itself.** Re-run unchanged on
`P27_PalmDesk` → Position, 132 accessibility attributes scanned:

| Check | 07:05 | 08:20 |
|---|---|---|
| business-day count present | **false** | **true** |
| formatted MTM present | **false** | **true** |
| open positions alt present | — | **true** |
| error visuals | 0 | 0 |

Resolved altText now appears in the accessibility tree — `" Book mark-to-market at 2026-08-28:
-168,330 MYR."`, `" Open positions on the book: 449."`, `" USDMYR at the latest business day in
context: 4.4205."` — where an hour earlier the only match was the `CapTrend` caption textbox.

**Inventory intact:** `list_items` unfiltered → **9 items**, `SM_PalmDesk` still
`f02c8481-f606-41b8-9026-b09ca1932258`. **The byPath publish overwrote in place and created no
duplicate dataset** — the risk flagged in the hand-off did not materialise.

## F-43 MITIGATED — publish without saving and the schema pin survives

F-43 recorded that a Desktop save rewrote 30 of 56 visuals from the pinned `visualContainer` 2.11.0
to 2.12.0. **This publish rewrote nothing:**

| Package | visualContainer | `.pbi/localSettings.json` |
|---|---|---|
| `P27_PalmDesk_publish/` (byConnection) | 26 × 2.11.0 + 30 × 2.12.0 | 06:55 — saved |
| `P27_PalmDesk_pbip/` (byPath) | **56 × 2.11.0 — untouched** | **absent — never saved** |

No file under `P27_PalmDesk_pbip/` has an mtime after 07:30. **Desktop rewrites the report on
*save*, not on open-and-publish** — so a publish that goes straight from open to Publish leaves the
pinned schema intact. Warning baseline holds at **0 errors / 7 warnings**.

**F-40, F-41 and F-42 all stand as written.** They are why this took a second attempt, and the
instrument F-40 produced is what made the second attempt verifiable in one page load instead of
another hour of inference. The `AltProof` card stays in place — now as a *passing* regression test.
