# FINDINGS — Session 2 (2026-09-06, Phase 2: model, report, alerts)

Continues the numbering from `FINDINGS_S1.md` (F-1 … F-14). Every finding names the command or
call that established it (App C 18). Destinations marked → are dual-write targets.

---

## F-15 — A Direct Lake model created through Core MCP fails with `Missing_References`, and framing is NOT the cause → SETTLED (replaces the S1 row), CHANNELS

**This closes the S1 leading hypothesis, negatively.** S1 guessed "never framed". That guess is now
disproven by measurement.

What was run, in order:

| # | Action | Result |
|---|---|---|
| 1 | `create_item` SemanticModel `SM_PalmDesk`, 14 parts, Direct Lake over `WH_PalmDesk` (P24's `AzureStorage.DataLake` shape, GUID path, CRLF) | **Succeeded**, LRO `79700813-…`, 11.2 s → `f02c8481-f606-41b8-9026-b09ca1932258` |
| 2 | `update_item_definition`, 17 parts — 12 tables, 108 columns, 13 relationships, **50 measures** | **Succeeded**, LRO `c0ff4038-…`, 3.5 s |
| 3 | `create_item` Report `RPT_PalmDesk_Check`, 11 parts, bound `byConnection` to the model | **Succeeded**, LRO `18281769-…`, 0.44 s |
| 4 | Opened the report in Chrome | All four data visuals: *"Something's wrong with one or more fields… (MTM Daily) MTM (MYR)"* — **the S1 symptom, reproduced on a completely different model** |
| 5 | Clicked *See details* → *See details* (the step S1's frozen renderer never reached) | **`Underlying Error: Missing_References`**. Activity `391ef543-…`, service 13.0.28514.444, cluster `wabi-malaysia-west-a-primary-redirect` |
| 6 | **Refresh now** on the `SM_PalmDesk` row in the workspace list (the framing test) | Fired; the row's Refreshed stamp is populated |
| 7 | Re-opened the report in a fresh tab | **Identical `Missing_References`.** |

**Verdict: creatable, updatable and readable back through Core MCP; it does not answer, and a
portal refresh does not fix it.** The error is not "no data" — it is that the report's field
references cannot be resolved at all, which is what you would see if the definition were stored but
the tabular database never materialised. Two hypotheses remain open and are **not** ranked by
evidence, only by cheapness to test:
- **(b)** the OneLake/`sourceLineageTag` binding shape differs for a **Warehouse** (P24 proved the
  shape on a **Lakehouse**; S1's probe and this model are both Warehouses — the only two failures
  this engine has);
- **(c)** a missing model-level Direct Lake annotation.

**The comparator that would settle it in one read was attempted and could not be obtained:** creating
one Direct Lake model through the portal over the same Warehouse and reading its TMDL back with
`get_item_definition`. The affordance lives in the Warehouse ribbon, which is canvas-drawn (F-18).
**This is the single highest-value first move for Session 3**, and it needs one human click.

*Not tested, and it matters:* `definition.pbism` version `5.0` with `compatibilityLevel: 1702` (the
shape Core MCP's own `get_knowledge` documents today). The engine has only ever submitted `4.0`/`1606`.
The re-push carrying that change failed on payload transcription (F-17), not on the tenant.

## F-16 — The service REWRITES the semantic-model definition on ingest; a CRLF round-trip does not survive → GUIDE, CORE_RULES

`get_item_definition` on `f02c8481-…`, decoded and compared against exactly what was submitted:

| Submitted | Stored | Consequence |
|---|---|---|
| `definition.pbism` `"version": "4.0"` | **`"4.2"`** | The version you write is not the version you get. Never quote a stored version as evidence of what was sent |
| `database SM_PalmDesk` | **`database`** (bare) | The database name lives in item metadata / `.platform`, not in TMDL |
| every `.tmdl` with **CRLF** | **LF on all of them, zero exceptions** | **The engine's standing "CRLF on all `.tmdl`" rule is a local-authoring and Desktop concern only.** It is erased by a service round-trip and cannot be asserted about a deployed item |
| 17 parts | **18 parts** — an unsolicited `.platform` (type, displayName, description, all-zero `logicalId`) | Any part-count reconciliation must expect it |
| `compatibilityLevel: 1606` | `1606` | Preserved — so the rewriting is selective, not wholesale |

Also observed: the `.platform` description was **stale** — it still read "9 tables … 10 relationships"
from the create call after an update took the model to 12 and 13. `update_item_definition` does not
refresh item metadata unless `UpdateMetadata` is set.

## F-17 — Core MCP item size is bounded by inline base64 transcription, not by the API → CHANNELS, SETTLED

Measured this session, same tool, same folder shape:

| Payload | Parts | Outcome |
|---|---|---|
| 31,248 B base64 | 14 | Succeeded |
| 53,996 B | 17 | Succeeded |
| 18,840 B | 11 | Succeeded |
| **54,032 B** | 17 | **Failed twice**, `CorruptedPayload` / `isRetriable:false`, no LRO issued — the tool call truncated after 5 of 17 parts and corrupted the `relationships.tmdl` base64 |
| **160,224 B** (the 4-page report) | 65 | **Not attempted** — three times the size that already failed |

The 54 KB pair is the finding: **the same size succeeded and failed on the same day**, so ~50 KB is
not a limit, it is the edge of reliability. `CorruptedPayload` is atomic and non-retriable, so nothing
was written — but the failure mode is silent truncation inside the agent, not an API rejection, and
no validator sees it.

**Rule for Type D planning:** an item whose definition exceeds roughly 30 KB of base64 cannot be
deployed dependably through Core MCP from a session, and this tenant has no streaming alternative
(Fabric REST / `fab` / `az` are unreachable — SETTLED 2026-09-06). **Decide at Phase 0 how reports
reach the service; do not assume `create_item` scales with the report.** For P27 the consequence was
concrete: the 4-page report ships as a `.pbip`, not as a service item.

## F-18 — Fabric's canvas editors remain unactionable; confirmed on a SECOND surface → CHANNELS (strengthens the S1 F-8 row)

Two more attempts today, both ending the same way as S1's two:
- **Warehouse ribbon** (`/warehouses/<id>?experience=fabric-developer`, 18 s settle): `find` for
  "New semantic model" — *no such element in the accessibility tree*. This is a **new surface**; S1
  only established it for notebooks.
- **Notebook ribbon** (`/synapsenotebooks/696a234f-…`, 40 s settle across two waits): `find` for
  "Run all", then for *any* notebook toolbar command — **nothing in the tree either time**.

Four attempts, two different Fabric artefact editors, zero elements. **Treat "act on a Fabric
artefact editor by browser" as closed, not as flaky.**

## F-19 — …but the Power BI–experience pages ARE fully actionable, and that distinction is the useful one → CHANNELS

The S1 conclusion "browser reading works, browser acting does not" is **too broad**. Everything below
was read *and acted on* today through the accessibility tree, first attempt, no coordinate clicks:
- workspace item list — every row, its links, and its per-row commands;
- **`Refresh now` on the semantic-model row — clicked, and it fired** (F-15 step 6);
- the semantic-model settings page (Gateway connections, Data source credentials, Refresh, …);
- the report error dialog, including the nested *See details* that yielded `Missing_References`.

**The line is not read-vs-act. It is `app.powerbi.com` Power BI–experience pages (DOM, actionable)
versus Fabric artefact editors (canvas, not actionable).** Route UI work accordingly, and stop
budgeting retries for the canvas half.

## F-20 — `validate_pbip.py` MEASURE_HARDCODED_YEAR fired on prose in `///` descriptions → ENGINE FIX (shipped), GUIDE

A measure block was delimited from `measure X =` to the next `measure|column|partition|hierarchy`
keyword, which **swallowed the `/// description` lines written above the *next* measure**. Any date in
a description ("frozen 2026-09-06") was then scanned as that measure's DAX. It fired on three P27
measures whose DAX contains no year at all: `Sum of Buckets (MYR)`, `Realised P&L (MYR)`,
`Short Position (MT)`.

Fixed by ending a measure block at the first `///` as well as at the next object keyword — which
repairs all three measure-scoped checks, not only this one. **Both controls run, per the standing
rule:** a positive control (`YEAR(Calendar[biz_date]) = 2026` in real DAX) still fires; a
false-positive control (a clean `SUM()` measure preceded by a description containing `2026-09-06`)
no longer does. P27 re-run: **0 errors, the three false positives gone**, 119 visual.json of 119 read.

*This is exactly the App C 24 shape:* a check that reports a finding it cannot justify is as bad as
one that reports nothing, and only a false-positive control catches it.

## F-21 — The terminology sheet's bucket prose contradicts the delivered procedure; the artefact won → GUIDE (spec-reconciliation gate)

`TERMINOLOGY.md` lists the P&L-explained buckets as "new trades · cancellations/amendments · price ·
**time · FX** · unexplained". Read off `03_usp_run_eod.sql` (lines 60–101) the procedure computes
**b3 = FX** and **b4 = time**:
- `b2` = `(o.price − p.curve_price) × prior position × prior fx` — curve move at yesterday's tenor → **Price**
- `b3` = `(o.price − p.contract_price) × prior position × (w.fx − p.fx)` — **FX**, physicals only
- `b4` = `(w.curve_price − o.price) × prior position × today's fx` — one day of carry → **Time**

where `o` is the `req_kind = 'O'` request, confirmed at line 44 to be *yesterday's tau priced on
today's curve*. Had the prose been trusted, every bucket caption on the attribution page would have
been mislabelled, and no validator in this engine would ever have caught it — the numbers would all
have tied. **The gate earned its cost here.**

## F-22 — Activator could not be reached in-session; rules are documented, not live → CONTRACT §3 row 5

The Activator remote MCP is per-artifact (`…/v1/mcp/workspaces/<WS>/reflexes/<ARTIFACT-ID>`,
channels §2d) and reaching it requires the user to add a connector in the Claude app and consent new
Entra scopes. That is a manual step mid-session, which contract §4 forbids waiting on. Taking the
next channel down — a Reflex definition through Core MCP — is blocked by the same payload ceiling
(F-17) and by having no verified Reflex definition shape to copy. **Reported, not hidden.** The two
rules and their thresholds are written into the contract at Rev 2 so S3 can fire them in one pass.

## F-23 — The local Power BI modeling MCP's `ConnectFabric` is unattended-hostile → CHANNELS

`connection_operations {operation: ConnectFabric, workspaceName: WS_PalmDesk_Dev,
semanticModelName: SM_PalmDesk}` → **`Device 'ywsbi' did not respond within 60s`**, and a follow-up
`ListConnections` returned **`Found 0 connections`**. The call is sitting on an interactive sign-in.
CLAUDE.md already says "attended sessions only"; this measures what that means — it does not fail
fast, it hangs and registers nothing. **Do not put `ConnectFabric` on an unattended path.** Had it
worked it would have been the session's best channel: it carries `Refresh`, `dax_query_operations`
and full TOM write in one connection.

## F-24 — Five hypotheses eliminated by controlled probe; what survives is sharp, and only the comparator reaches it → SETTLED (supersedes the F-15 row), CHANNELS

Run after the S2 close ritual, on the user's instruction to proceed. Two minimal Direct Lake models
over `WH_PalmDesk` — 2 tables, 2 measures, **~3.5 KB base64 each**, so the F-17 size ceiling cannot
confound anything — each differing from the failing baseline by **one** variable. Definitions kept at
`00_Plan/probe_s2/`. The measure's true value is known independently: `SUM(eng.attribution_daily
.d_mtm)` = **−168,329.67** over 120 rows.

| Probe | The one variable | Create | Render |
|---|---|---|---|
| **A** | `definition.pbism` **5.0** + `compatibilityLevel` **1702** | ✅ Succeeded, 13.4 s → `00567b74-7db4-4852-b895-805d0e2dcc3c` | ❌ **`Missing_References`** (23:20:06 +08, correlation `722cb196-…`) |
| **C** | OneLake path in **name form**, `/WS_PalmDesk_Dev/WH_PalmDesk.Warehouse`, instead of GUIDs | ❌ **Failed at create**, 10.5 s | n/a |

**Probe C's error is new and it is useful:**
`Dataset_Import_FailedToImportDataset` — *"Direct Lake mode requires a Direct Lake data source.
Tables in Direct Lake mode must be the SQL or OneLake datasource kind. Please verify and fix the data
source definitions of the following Direct Lake tables, Calendar, Attribution Daily."*

### What is now eliminated

| # | Hypothesis | How it died |
|---|---|---|
| a | Never framed | Portal `Refresh now` fired; render unchanged (F-15) |
| — | Model size or complexity | 1-table (S1), 2-table (Probe A) and 12-table (`SM_PalmDesk`) models all fail identically |
| d | `definition.pbism` version skew | **Provably untestable through this channel.** Submitted `4.0` → stored `4.2`; submitted `5.0` → stored `4.2`. Two different inputs, one output: the service *overwrites* the field with its own current value. It is not clamping or incrementing |
| — | `compatibilityLevel` | **Honoured** (1702 submitted, 1702 stored — unlike `version`) and **1606 and 1702 both fail**. So it is a real variable, and it is not this one |
| b′ | Name-form OneLake path | Rejected **at create**, Probe C above |
| e | Unbound cloud connection / missing credentials | The settings pane shows the source **is** recognised — `AzureDataLakeStorage{"server":"<ONELAKE-HOST>","path":"/b06ab341-…"}` — mapped to **"Default: Single Sign-On (Entra ID)"**. Clicked **Apply** to commit the mapping explicitly, re-rendered: **unchanged** |

### What survives, and why it is now a much better question

Probe C proves the service **validates the Direct Lake datasource kind at create time** — and it
*accepts* our GUID path. So the **data source is correct**; what fails is the **table binding**, at
query time, after a source the service itself approved.

That points at the one part of the TMDL this engine has always synthesised rather than copied:
**`sourceLineageTag`.** We write `[eng].[attribution_daily]` on the table and the bare column name on
each column, because that is what P24's example contained. In a service-authored Direct Lake model
`sourceLineageTag` is the service's own identifier for the delta table and its columns — and if it is
an opaque identifier rather than a two-part name, a synthesised string would resolve to nothing,
which is precisely `Missing_References` on *every* field of *every* table while the datasource itself
validates clean. **This is hypothesis (f) and it is the leading one.**

It cannot be tested by guessing — the whole point is that the value is the service's, not ours. **One
portal-created Direct Lake model over a Warehouse, read back with `get_item_definition`, settles it.**
That is the ask already in `HANDOVER_S2.md` §5 item 1; this finding raises it from "highest value" to
"the only remaining route", and tells S3 exactly which three lines of the diff to look at first:
the table's `sourceLineageTag`, the columns' `sourceLineageTag`, and the partition's `entityName` /
`schemaName` pair.

**Left in the tenant deliberately** (not deleted — they are the evidence, and S3's inventory
reconciliation should expect them): `SM_Probe_A` `00567b74-…` and `RPT_Probe_A`
`58c0970b-cd72-49ea-920c-57ba3fd01f01`. `SM_Probe_C` never created.

## F-25 — A real defect found against Microsoft's own docs; it did NOT resolve the failure, and saying so is the point → GUIDE, CHANNELS

Triggered by the user's model-view screenshot, which changed the shape of the problem: **the web
modeling view renders all 12 tables with their columns, all 13 relationships and the measures, with
a warning triangle on every table.** So the model is *not* empty and its metadata *is* loaded — the
"stored but never materialised" reading from F-15 is wrong. Something resolves the model fine; only
the table→source binding fails.

**Then the docs, which this engine had not consulted on this question.**
`microsoft_docs_search` → *Lineage tags for Power BI semantic models*, verbatim:

> "For DirectLake models, the `sourceLineageTag` must be the name of the table/column in the
> Lakehouse/data warehouse."

This engine wrote `sourceLineageTag: [eng].[attribution_daily]` on every table — the two-part
bracketed form. **That is wrong against the documentation.** (Columns were already bare names and
were always correct.) The form was inherited from a Direct Lake **on SQL** example, where a two-part
name *is* right; it is not right for Direct Lake **on OneLake**.

**Tested properly, on the probe, one variable:** rewrote the two table tags to `attribution_daily`
and `calendar`, `update_item_definition` (Succeeded, 1.9 s, LRO `c42c705e-…`), re-rendered →
**`Missing_References`, unchanged**. Then fired **`Refresh now`** (the docs say Refresh performs a
schema refresh *and* reframes Direct Lake tables) and re-rendered → **unchanged again**.

**So: a genuine defect, corrected, that is not the cause — or not the whole cause.** It is recorded
as a defect anyway and fixed in `04_Model/build_tmdl.py` and in the delivered `.pbip`, because
"it didn't fix the bug" is not a reason to ship something the vendor's documentation says is wrong.
The distinction matters for S3: **do not read the fix as a failed hypothesis and revert it.**

**Two further doc facts worth carrying:**
- The documented Direct Lake on OneLake expression is
  `AzureStorage.DataLake("https://onelake.dfs.fabric.microsoft.com/<wsId>/<itemId>")` — **with no
  `[HierarchicalNavigation=true]`**. This engine (and P24) pass that option. Untested as a variable.
- *"Direct Lake on SQL connection expression … must refer to the SQL analytics endpoint by GUID, not
  by friendly name."* Independent confirmation of Probe C's create-time rejection (F-24).

**What is now blocked, precisely.** The model view carries a per-table warning whose text would very
likely name the cause, and its **DAX query view** would return a far more specific error than a
report visual does. **Neither is reachable from a session**: the web modeling experience is
canvas-drawn — `find` returns nothing and `get_page_text` returns *"No text content found. Page may
contain only images, videos, or canvas-based content."* This is F-18's boundary hit for the fifth
time, now on the modeling surface.

**The two reads that would end this**, both ~15 seconds for a human with the model already open:
hover any table's warning triangle in the Data pane and report the tooltip; and in **DAX query view**
run `EVALUATE ROW("t", [Delta MTM (MYR)])` and report the error verbatim. Either is worth more than
another elimination round.

## F-26 — The two user-supplied reads: one is boilerplate, one is real → GUIDE, CHANNELS

The user ran both reads F-25 asked for. They resolve in opposite directions, and separating them
mattered.

**(a) The per-table warning triangle is GENERIC. Do not chase it.** Tooltip, verbatim:

> "DAX queries may fall back to DirectQuery, if allowed, or show errors. To fix this, try refreshing
> the semantic model, scaling up the capacity, or avoid using SQL endpoint items, such as views."

That is the standard Direct Lake advisory shown on **every** Direct Lake table in web modeling — it
is about the *possibility* of fallback, not about this model. It carries no model-specific
information, and none of its three suggested fixes applies here (refresh: done twice, no change;
capacity: a trial FTL64 against 36k rows; views: this model binds tables, not views). **F-25 treated
these triangles as the likely diagnosis; that was wrong, and the correction is the finding.**

**(b) The DAX query view error is real and specific.** `EVALUATE ROW("t", [Delta MTM (MYR)])` →

> Query (1, 19) The value for 'Delta MTM (MYR)' cannot be determined. Either the column doesn't
> exist, or there is no current row for this column.

Column 19 is the `[` of the measure reference. This is DAX **name resolution** failing: when no
measure of that name exists, DAX falls back to reading `[X]` as a column reference and reports
exactly this. So at query time the engine has no measure `Delta MTM (MYR)` — even though the stored
definition demonstrably carries 50 measures (read back in F-16) and the modeling canvas draws them.

**Also established: DAX query view is a real query channel against this model** — it returns precise
engine errors, unlike a report visual's generic "Something's wrong". It is canvas-only, so a session
cannot drive it, but it is the highest-value read a human can take on this class of problem. Ask for
it first next time, not last.

## F-27 — The column-only discriminator: the TABLES do not load; the measures are fine → SETTLED (supersedes F-24's framing)

F-26(b) looked like a measure defect. It is not, and one cheap experiment proved it.

Rebuilt `RPT_Probe_A` with four data visuals chosen to isolate one thing each:

| Visual | Binds | Touches a model measure? |
|---|---|---|
| `ColOnly` (`tableEx`) | `Calendar[biz_date]` only | **No** |
| `ColCount` (`cardVisual`) | implicit count over `Calendar[day_index]` | **No** |
| `Card` | `[Probe Delta MTM]` | Yes |
| `Mx` | `Calendar[biz_date]` × `[Probe Delta MTM]` | Yes |

**Result: all four error.** The two that never reference a measure fail exactly like the two that do.

**Therefore the Direct Lake tables do not load at all, and F-26(b) is a downstream symptom** —
measures defined on a table that fails to load are not resolvable by name, which is precisely the
error DAX returned. **The 50 measures are not implicated.** F-24 and F-25 were both looking at the
wrong layer; this is the first evidence that names the right one.

**And the last variable in our control is now also eliminated.** Microsoft's Direct Lake on OneLake
migration doc shows the expression *without* an options record; this engine (and P24) pass
`[HierarchicalNavigation=true]`. Removed it, pushed (Succeeded, LRO `4347b9dc-…`), fired a reframing
`Refresh now`, re-rendered: **all four still error.**

*Honest caveat, raised by the subagent and worth keeping:* the probe item now carries **two**
doc-recommended changes made without a render between them — bare `sourceLineageTag` (F-25) and the
dropped navigation option. They are confounded on that item. Both are kept because both are correct
against the documentation, but if a later run makes it work, **attribution requires a decontamination
pass**, not an assumption.

### The new leading hypothesis (h), and it is documented

Microsoft's *Develop Direct Lake semantic models*, on the creation dialog for a Warehouse / SQL
analytics endpoint:

> "This dialog defaults to **Direct Lake on OneLake** if the SQL analytics endpoint is in **user
> identity mode**, or **Direct Lake on SQL** if the SQL analytics endpoint is in **delegated mode**."

And the two storage modes use **different connectors**: Direct Lake on OneLake uses
`AzureStorage.DataLake(...)`; **Direct Lake on SQL uses `Sql.Database("<SQL endpoint connection
string>", "<SQL analytics endpoint id>")`**.

**Every model this engine has ever built — P24's, S1's gate probe, `SM_PalmDesk`, both S2 probes —
uses the OneLake form.** If this tenant's Warehouse endpoint is in delegated mode, the OneLake form
is simply the wrong storage mode for this source, and no amount of tuning it will work. That fits
every observation: the definition validates (the URI *shape* is a legal OneLake datasource — Probe C
proved the service checks that much), the metadata loads, and the tables never bind.

**Blocking input, and it is small.** Both hypothesis (h) and the pragmatic Import-mode fallback need
the same one thing: **the Warehouse's SQL connection string**. It is not obtainable from a session —
`SERVERPROPERTY('ServerName')` through the DW MCP returns only the workspace GUID
(`b06ab341-…`, not the `*.datawarehouse.fabric.microsoft.com` host), and "Copy SQL connection
string" is absent from the workspace-list DOM menu. One copy-paste unblocks two routes at once.

## F-28 — The engine's own linter caught a generator defect before it reached a delivered page → ENGINE FIX (shipped)

`06_Report/pbir.py` emitted `drillFilterOtherVisuals: true` on **every** visual it generated. Guide
§24a / `validate_pbip.py`'s `DRILL_ON_TABLEEX` rule: that property is invalid on visual types that
cannot drill. It surfaced only when the S2 discriminator probe used a `tableEx` for the first time —
the delivered 4-page report happens to use `matrix`, `cardVisual`, `columnChart`, `lineChart`,
`waterfallChart` and `textbox`, none of which tripped it.

Fixed at the generator, not the file: `pbir.py` now carries a `NO_DRILL` set
(`tableEx`, `textbox`, `pageNavigator`, `actionButton`, `shape`, `image`, `card`) and omits the
property for those types. Re-run: **0 errors** across 124 visual.json of 124 read.

**Worth noting how this was caught.** The linter fired on a throwaway diagnostic artefact, not on a
deliverable — which is the argument for running the full-project validator over probe folders too,
rather than scoping it to the delivery folder. A generator defect that only shows on a visual type
you have not used yet is invisible until the day you use it, and that day is usually not a day you
are looking for it.

## F-29 — SOLVED: this Warehouse binds through Direct Lake ON SQL, not Direct Lake on OneLake → SETTLED (closes the S1 F-5 / S2 F-15 thread), CHANNELS, GUIDE

**The connector was wrong the whole time.** Every Direct Lake model this engine has ever built —
P24's, S1's gate probe, `SM_PalmDesk`, both S2 probes — used the **Direct Lake on OneLake**
connector `AzureStorage.DataLake(...)`. Against a Fabric **Warehouse** on this tenant that form
validates on create, loads its metadata, draws in the modeling canvas — and never binds a single
table. Swapping one line to the **Direct Lake on SQL** connector fixed it outright:

```
Sql.Database("<SQL-ENDPOINT>.datawarehouse.fabric.microsoft.com",
             "43516adb-2f22-46e6-8fa4-3ad499483171")
```

**Attribution is clean, and that matters given how many changes were in flight.** The two other
doc-driven changes were each pushed, refreshed and *rendered on their own* before this one, and
**both still failed**: bare `sourceLineageTag` (F-25) and the dropped `[HierarchicalNavigation=true]`
(F-27). Only the connector swap moved it. Both other changes are kept — they are correct per the
documentation — but neither was necessary or sufficient.

### The evidence, against Warehouse truth computed independently

`RPT_PalmDesk_Check` on the real `SM_PalmDesk` (12 tables, 108 columns, 13 relationships, 50 measures):

| Measure | Rendered | Warehouse | |
|---|---|---|---|
| MTM (MYR) | −168K | −168,329.67 | ✅ |
| Open Positions | 449 | 449 | ✅ |
| Delta MTM (MYR) | −168K | −168,329.67 | ✅ |
| Attribution Residual (MYR) | **0.00** | 0.00 | ✅ |
| Max Absolute Unexplained (MYR) | 312.50K | 312,499.98 | ✅ |
| Days Outside Tolerance | 3 | 3 | ✅ |
| Exposure (MYR) | 1bn | 1,120,348,981.90 | ✅ |
| Counterparties in Breach | 4 | 4 | ✅ |
| Peak Utilisation | 236.7% | 2.3666 | ✅ |
| Assessments / Effective | 27 / 26 | 27 / 26 | ✅ |
| Contracts | 549 | 549 | ✅ |
| Physical / Futures MTM | 151K / −320K | 151,420.33 / −319,750.00 | ✅ |
| Net Position (MT) | −84.3K | −84,269.950 | ✅ |
| USDMYR Rate | 4.4205 | 4.420455 | ✅ |

**The zero-relationship probe PASSES** (the check the preflight mandates, and the one both validators
are blind to): the bucket matrix returns six *different* values summing to **−168,330 = ΔMTM**
(New trades −1,239,128 · Price −1,634,890 · FX 506,667 · Time 3,147,264 · Amendments −314,743 ·
Unexplained −633,500), and the segment matrix splits BUYER 1,119,906,136 / SUPPLIER 442,846.
Identical numbers on every row would have meant no working relationship; these are not identical.

### The §132 pixel gate, satisfied for the visual vocabulary

`P27_PalmDesk_Smoke` (`ada62c43-0def-4831-91ed-8cb4afbac648`) — a two-page cut chosen because between
them Position and Attribution exercise **every visual type the 4-page report uses**:
`waterfallChart`, `columnChart`, `lineChart`, `matrix`, `cardVisual`, `textbox`, `pageNavigator`.
**All render, zero errors**, including the waterfall's six buckets and Total, and the `USDMYR Rate`
card — the only card touching the `mkt` schema, which no probe had exercised. All four warehouse
schemas (`eng`, `ref`, `trd`, `mkt`) are now proven through the model.

### The rule this leaves behind

**Choose the Direct Lake connector by what the SOURCE is, and prove it with a two-table probe before
building anything on it.** Microsoft's docs pair them explicitly — Direct Lake on OneLake uses the
Azure Data Lake Storage connector, Direct Lake on SQL uses the SQL Server connector — and note that
the creation dialog picks between them by whether the SQL analytics endpoint is in *user identity*
or *delegated* mode. This engine copied P24's Lakehouse-proven OneLake shape onto a Warehouse and
carried the error across three projects' worth of assumptions. **A two-table probe would have caught
it in ten minutes on day one; instead it cost most of two sessions.**

## F-30 — The Core MCP payload ceiling, bracketed → CHANNELS, SETTLED (supersedes F-17's estimate)

F-17 put the edge at "~50 KB, and unreliable". Four more pushes bracket it properly, and the
limit is **not** the API, the part count, or transport — it is how much base64 an agent can emit in
one tool call:

| Push | Parts | base64 | array JSON | Result |
|---|---|---|---|---|
| `P27_PalmDesk_Smoke` | 35 | 41,076 | 44,636 | ✅ first attempt |
| `SM_PalmDesk` (final) | 17 | 53,864 | 55,333 | ✅ first attempt |
| `P27_PalmDesk` (full) | 65 | 76,064 | **82,646** | ❌ **could not emit — no request was ever issued** |

**Part count is irrelevant** — 35 parts went through more easily than 17, because the 35-part payload
was smaller. **Array JSON is the metric.** ~55 KB is reachable; ~83 KB is not, and the failure at
that size is *deterministic*, not stochastic: retrying is pointless, and the two earlier
`CorruptedPayload` rejections at ~54 KB were the same wall caught one layer later, as truncation
that was transmitted anyway.

**Planning rule (supersedes F-17's):** budget **array JSON ≤ ~50 KB** per Core MCP item push, and
size the deliverable to it at Phase 0. Compacting JSON (`separators=(',',':')`) buys ~53% and is
free — the on-disk artefact keeps its readable form; only the deployment twin is compacted. Beyond
that, the honest options are a `.pbip` for one manual import, splitting into several items, or a
streaming channel (`fabric-cicd`/`fab`) this tenant cannot reach.

## F-31 — The `.pbip` shortcut file was hand-written from memory and Desktop rejected it → ENGINE FIX (lint rule shipped), GUIDE

Power BI Desktop refused to open the delivered `.pbip`:

> Expected '$schema' property in '…\P27_PalmDesk.pbip' to follow patterns:
> `^https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.[0-9]+.[0-9]+/schema.json$`
> `UnrecognizedSchemaVersion: Path: PBIP Shortcut`

The engine had written `…/json-schemas/fabric/**item**/pbipProperties/1.0.0/schema.json`.

**The trap is precise and it is a good one.** Fabric uses **`/fabric/item/`** for the parts *inside*
the package — `definition.pbism`, `definition.pbir` — and **`/fabric/pbip/`** for the `.pbip`
shortcut itself. Having just written two correct `item` URLs, the third looks right. It parses, it
passes `json.load()`, and **nothing in this engine could catch it**: the `.pbip` never goes to the
service, so the service validator never sees it either. Only Desktop does.

**This is the standing rule violated exactly as written** — *"never hand-write shapes from memory —
grep a delivered sibling project"* (CLAUDE.md, guide §48a). Three delivered projects (07
GlobalEnergy, 12 NimbusTel, 16 CreditRiskAnalytics) carried the correct URL the whole time.

### Fixed, and made mechanical

- `.pbip` corrected, and **`build_report.py` now owns its generation** — it was previously a one-off
  heredoc, which is how it escaped review. It is regenerable and carries the URL with a comment
  naming the `item`-vs-`pbip` trap.
- **New `validate_pbip.py` rule `PBIP_SCHEMA_URL`** (ERROR), plus `PBIP_SCHEMA_MISSING` and
  `PBIP_NO_ARTIFACTS`. The message names the `item`/`pbip` confusion explicitly, because that is the
  actual failure mode, not a generic "bad schema".
- **Both controls run:** a `.pbip` with the `item` URL fires; one with the `pbip` URL is silent.
- **Scan floor updated (App C 24):** the scan line now reports `pbip` volume, and a folder holding
  only `.pbip` files no longer trips FLOOR FAILED — a check that read two files must not report the
  same as one that read nothing.

### The rule immediately found three latent defects elsewhere

A corpus sweep of all 26 `.pbip` files found **three with no `$schema` property at all** — two copies
of `HRAnalytics.pbip` (Project 09) and `OilGas-EP-Analytics.pbip` (Project 10). Desktop would reject
those the same way. **They are NOT touched here** — they belong to other projects, this session has
not examined them, and silently editing three unrelated deliverables is exactly the blast-radius
mistake App C 27 warns about. Reported for their own sessions; `weekly_scan.py` will now surface
them mechanically.

**This is the mechanically-detectable-lesson rule paying for itself inside one session:** the lint
rule was written to stop a defect recurring, and found three instances of it that predated the bug
that prompted it.

**Not yet verified:** the corrected `.pbip` has not been opened in Desktop. The URL now matches the
pattern Desktop's own error quoted and matches 23 delivered files, but **Desktop is the test** — the
whole point of this finding is that nothing else can see this class of defect.

## F-32 — A `byPath` `.pbip` can never metadata-match a model that has been through the service → GUIDE, and it changes which package we ship

**F-31 closed:** with the `$schema` corrected the `.pbip` opens in Desktop. Confirmed by the user
2026-09-07. Desktop was the only validator for that defect and it has now passed.

**But opening it surfaced a second, structural problem.** Desktop showed two dialogs:
1. *"Set up the remote model for your PBIP"* — Direct Lake models cannot be authored locally, so a
   `.pbip` carrying one must bind to a workspace model.
2. *"The PBIP and semantic model metadata don't match — Choose a new semantic model or overwrite the
   current one."*

**That mismatch is not a defect and it is not fixable.** F-16 measured exactly why: the service
**rewrites a definition on ingest** — `pbism` version forced to `4.2`, the `database` name stripped,
every `.tmdl` normalised CRLF→LF, an unsolicited `.platform` part added. A local folder therefore
*cannot* byte-match the same model after it has been deployed. **Any `byPath` `.pbip` pointing at a
model that has been through the service will always show this dialog.**

**"Overwrite the current model" was declined, deliberately.** It would push the local TMDL over the
live `SM_PalmDesk` — the model proven against Warehouse truth on 14 of 14 measures — to fix a
cosmetic mismatch caused by the service's own rewriting. No upside, non-zero risk, two days before
the E3 deadline.

### The rule this produces

**Ship the report as a report-only `.pbip` bound `byConnection` when the model already lives in the
service; use `byPath` only when the model must be created locally.**

`06_Report/P27_PalmDesk_publish/` is that package — 66 files, no `SemanticModel` folder,
`definition.pbir` bound `byConnection` to `semanticmodelid=f02c8481-…`. Desktop has nothing to
reconcile, so neither dialog fires; it opens live-connected and **Publish uploads the report alone**.
`validate_pbip.py`: 0 errors, 56 visual.json of 56 read.

Both packages are kept and they are not redundant:

| Package | Binding | Use it when |
|---|---|---|
| `P27_PalmDesk_publish/` | `byConnection` → live `SM_PalmDesk` | **Default.** The model is in the service. Publish sends the report only |
| `P27_PalmDesk_pbip/` | `byPath` → local `SM_PalmDesk.SemanticModel` | The model must be rebuilt from scratch — a fresh tenant, or after the trial expires |

This also settles the deployment question F-30 left open: the 4-page report cannot go through Core
MCP (82,646 chars against a ~55 KB ceiling), but **one Publish from the `byConnection` package puts
all four pages in the service** — no size limit, no manual import of a model.
