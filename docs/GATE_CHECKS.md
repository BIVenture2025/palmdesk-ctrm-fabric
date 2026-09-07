# Gate Check Results — Project 27 (PalmDesk)

**Session 1, 2026-09-06.** Type D availability gates, Skill 8 Phase 0b. Rule this file enforces:
**record what you ran to find out** (CORE_RULES App C 18). Nothing below is marked unavailable
without the command that established it; every gate has a positive AND a negative control.

Contract reference: `OUTCOME_CONTRACT_DRAFT.md` Rev 0.2 §3 (components) and §4 (constraints).
Tenant: **Malaysia West**. Capacity used for every probe: **`14e682a7-70e3-4636-a78c-76aaa2e11be1`**
(`Trial-20260222T155835Z-…`, FTL64, Active — the newest of two trial capacities returned by Core MCP
`list_capacities` at 04:36 UTC; the other, `63efd2af…` `Trial-20250909…`, is older).

Scratch workspace: `ClaudeGate_P27_Probe` = `c8516fa7-50da-4123-b03b-20e01bd49c02`, created 04:37:53 UTC,
**deleted 04:56:44 UTC**, absence confirmed by `list_workspaces` at 04:56:48 UTC (11 workspaces returned,
none by that name). All timestamps are the `Date:` header of the MCP response.

---

## 0. Channel reach — measured before anything else

| Channel | Status 2026-09-06 | Command that established it |
|---|---|---|
| **Fabric Core MCP** (in-session) | **LIVE — 29 tools** | `RefreshMcpTools` 04:35 UTC → `Fabric_Core_MCP: toolCount 29, added [], removed []` |
| **Fabric DW MCP** (in-session) | **LIVE — 1 tool (`execute_query`)** | `RefreshMcpTools` 04:35 UTC → `Fabric_DW_MCP: toolCount 1` |
| Built-in browser (Claude desktop app pane) | **NOT SIGNED IN to Fabric** — landed on the "Sign in \| Microsoft Fabric" email form | `Claude_Browser preview_start https://app.fabric.microsoft.com/home` → page text = sign-in form. Signing in needs a password, which the session will not enter → next channel down |
| **Claude in Chrome** (user's Chrome) | **LIVE, already signed in** | `navigate https://app.fabric.microsoft.com/home` → `find "trial"` returned button *"Trials activated: 27 days left"* at 04:40 UTC |
| `device_bash` (user's Linux VM) | LIVE | `session_preflight.py` ran (18 tools stamped) |
| Fabric REST / `fab` / `az` / OneLake | UNREACHABLE (SETTLED 2026-09-06, not re-derived) | — |

**Trial banner (contract §4):** *"Trials activated: 27 days left"* read **2026-09-06 04:40 UTC (12:40 MYT)**
via Chrome → expiry **≈ 2026-10-03**. Same reading as the planning session, one day later — the banner
had not yet ticked to 26 at that hour.

---

## 1. Gate 1 — Fabric Data Warehouse MCP: DDL + DML + EXEC — ✅ PASS

**Question:** does `mcp__Fabric_DW_MCP__execute_query` execute DDL, DML and `EXEC` (not only reads) against a
Warehouse created by Core MCP, and does a bad statement fail as a SQL error (tenant) rather than a
transport error (harness)?

Warehouse `WH_Gate_Probe` = `b59d31a3-50fb-4931-b64a-4512b74f09a3`, Core MCP `create_item` type `Warehouse`
→ 202, LRO `28cf7def…` Running at +5 s, **Succeeded at +9 s** (created 04:37:59, succeeded 04:38:08 UTC).

Every row below is one `execute_query(workspaceId=c8516fa7…, itemId=b59d31a3…, query=…)` call.

| # | Control | Statement (verbatim) | Result |
|---|---|---|---|
| 1 | +DDL | `CREATE TABLE dbo.gate_probe (id INT NOT NULL, label VARCHAR(50) NOT NULL, amt DECIMAL(18,2) NOT NULL);` | `Query returned 0 rows.` |
| 2 | +DML | `INSERT INTO dbo.gate_probe (id, label, amt) VALUES (1,'alpha',10.25),(2,'beta',20.50),(3,'gamma',30.75);` | `0 rows` |
| 3 | +READ | `SELECT COUNT(*) AS n, SUM(amt) AS total FROM dbo.gate_probe;` | **`3, 61.50`** |
| 4 | +DDL proc | `CREATE PROCEDURE dbo.usp_gate_probe @factor DECIMAL(9,4) AS BEGIN INSERT … SELECT id+100, 'proc_'+label, amt*@factor FROM dbo.gate_probe WHERE id<100; SELECT COUNT(*) AS n_after, SUM(amt) AS total_after FROM dbo.gate_probe; END` | `0 rows` |
| 5 | +EXEC | `EXEC dbo.usp_gate_probe @factor = 2.0;` | **`6, 184.50`** (= 61.50 + 2×61.50 ✓; the proc's result set came back through the tool) |
| 6 | **−object** | `SELECT id, label, amt FROM dbo.gate_probe_does_not_exist WHERE this_is_the_negative_control = 1;` | **`Error -32002: Invalid object name 'dbo.gate_probe_does_not_exist'.`** — SQL error, not transport |
| 7 | **−syntax** | `SELEC id FRM dbo.gate_probe;` | **`Error -32002: Incorrect syntax near 'FRM'.`** — SQL error, not transport |
| 8 | +batch DML | `UPDATE dbo.gate_probe SET amt = amt + 1 WHERE id = 1; DELETE FROM dbo.gate_probe WHERE id >= 100; SELECT COUNT(*) AS n, SUM(amt) AS total FROM dbo.gate_probe;` | **`3, 62.50`** — three statements in one call, last result set returned |
| 9 | +bulk | `INSERT INTO dbo.gate_probe (id,label,amt) VALUES (1000,'bulk_1000',1250.00),…,(1999,'bulk_1999',2498.75);` — **1,000 rows, 27,051 bytes, one call** (run by a subagent from `/scratchpad/bulk1000.sql`) | `0 rows`; then `SELECT COUNT(*), SUM(amt), MIN(id), MAX(id) … WHERE id>=1000` → **`1000, 1874375.00, 1000, 1999`** (= Σ(1250+1.25k), k=0..999 ✓) |
| 10 | +DDL view | `CREATE VIEW dbo.v_gate_probe AS SELECT id, label, amt*2 AS amt2 FROM dbo.gate_probe;` | `0 rows`; `SELECT COUNT(*) FROM dbo.v_gate_probe` → **`1003`** |
| 11 | +catalog | `SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA='dbo';` | `gate_probe BASE TABLE`, `v_gate_probe VIEW` |
| 12 | +DROP | `DROP VIEW dbo.v_gate_probe; DROP PROCEDURE dbo.usp_gate_probe; DROP TABLE dbo.gate_probe;` | `0 rows`; then `SELECT (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA='dbo')` → **`0`** |

**Three-way verdict: PASS.** Positive controls returned the arithmetically expected values; both negative
controls returned `-32002` SQL errors carrying the engine's own message text. The channel executes
DDL, DML, `EXEC`, views, multi-statement batches and 27 KB single statements.

**Trap found (recorded, not a failure):** a batch that mixes DDL with result-returning SELECTs —
`SELECT (SELECT COUNT(*) FROM dbo.v_gate_probe), (SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES …); DROP VIEW …; DROP PROCEDURE …; DROP TABLE …; SELECT COUNT(*) …`
— failed with **`Error -32002: The query references an object that is not supported in distributed processing mode.`**
The same DROPs as a DDL-only batch (row 12) and the same SELECTs alone (rows 10–11) all succeeded.
**Rule for the build: DDL batches contain only DDL; DML + SELECT may share a batch.**

**Cost fact for the load design:** the 27 KB statement cost the executing subagent ~105 k tokens for one
call (the text is read from disk AND emitted as the tool argument). Data volume through this channel
is paid twice in tokens; the generator keeps literals compact and the load runs in subagents, never in
the main context.

---

## 2. Gate 7 — SQL database in Fabric as the CTRM store — ❌ FAIL (kill criterion executed)

**Question:** does the DW MCP item-scoped `execute_query` run DDL against a **SQL database in Fabric** item?

| Step | Command | Result |
|---|---|---|
| Create | `create_item` type `SQLDatabase` `SQLDB_Gate_Probe` | 202 → LRO `c5afc931…` **Succeeded** (created 04:45:03, done 04:45:27 UTC, 24 s) |
| Read back | `list_items` | **two items appeared**: `SQLDatabase` `d35f6733-eb7e-4028-9174-edf4d2ae961e` **and** a companion `SQLEndpoint` `f17547a6-9338-4557-b1f1-b8c701477d9c` (same display name) |
| +READ via DB id | `execute_query(itemId=d35f6733…, "SELECT DB_NAME() AS db, @@VERSION AS ver")` | `SQLDB_Gate_Probe`, **`Microsoft Azure SQL Data Warehouse (RTM) - 12.0.2000.8`** — the *analytics-endpoint* engine string, not Azure SQL |
| −DDL via DB id (PK) | `CREATE TABLE dbo.gate7_probe (id INT NOT NULL PRIMARY KEY, label VARCHAR(50) NOT NULL);` | `-32002: The PRIMARY KEY keyword is not supported in the CREATE TABLE statement in this edition of SQL Server.` |
| −DDL via DB id (no PK) | `CREATE TABLE dbo.gate7_probe (id INT NOT NULL, label VARCHAR(50) NOT NULL);` | **`-32002: The external policy action 'Microsoft.Sql/Sqlservers/Databases/Schemas/Tables/Create' was denied on the requested resource.`** |
| +READ via endpoint id | `execute_query(itemId=f17547a6…, "SELECT DB_NAME(), SERVERPROPERTY('EngineEdition')")` | `SQLDB_Gate_Probe`, **`11`** (= Fabric/Synapse SQL analytics endpoint) |

**Verdict: FAIL for the intended use.** Passing either the `SQLDatabase` item id or its `SQLEndpoint` id
resolves to the **read-only SQL analytics endpoint** of the database, never to the OLTP database itself.
Reads work; DDL is denied by policy. This matches Learn (Warehouse + SQL analytics endpoint are the
documented targets) and now has a measured answer.
**Kill criterion (§3 row 7) executed:** the Warehouse is the CTRM store; component 7 dropped, no regret.
Nothing was built against it.

---

## 3. Gate 2 — Open mirrored database (`GenericMirror`) via Core MCP — ✅ PASS (create/read-back)

| Step | Command | Result |
|---|---|---|
| Create | `create_item` type `MirroredDatabase` `OMD_Gate_Probe` with one part `mirroring.json` = `{"properties":{"source":{"type":"GenericMirror","typeProperties":{}},"target":{"type":"MountedRelationalDatabase","typeProperties":{"defaultSchema":"dbo","format":"Delta"}}}}` | **201 synchronous**, id `651f3790-60c1-4254-b528-13009e4f4b99` at 04:46:55 UTC (no LRO) |
| Read back (definition) | `get_item_definition` | 2 parts: `mirroring.json` decodes to the same JSON (server re-indented it, CRLF), `.platform` = `{"$schema":…/platformProperties/2.0.0/…, "metadata":{"type":"MirroredDatabase","displayName":"OMD_Gate_Probe",…},"config":{"version":"2.0","logicalId":"00000000-…"}}` |
| Read back (list) | `list_items` | `MirroredDatabase 651f3790…` **plus** an auto-provisioned companion `SQLEndpoint` `58ccb508-67c6-44e5-beb7-6751ef94754e` named `OMD_Gate_Probe` |
| Negative control | — none needed for creatability; the negative control for this component is the **landing-zone replication test in §6 of the session plan** (notebook writes → replicated row counts), which is what the kill criterion is written against | — |

**Verdict: PASS for creatability; replication is the build-time test.** Two facts the build uses:
(1) `get_item` on a MirroredDatabase through Core MCP returns **no `properties`** (no `oneLakeTablesPath`,
no `sqlEndpointProperties`) — the landing-zone path must be constructed as
`https://onelake.dfs.fabric.microsoft.com/<workspaceId>/<mirroredDbId>/Files/LandingZone`; (2) the mirrored
database's **own SQLEndpoint item id is listed**, so replicated row counts can be read through the DW MCP
without the portal.

---

## 4. Gate 3 — Direct Lake semantic model from TMDL via Core MCP — ✅ create PASS · ⚠️ render UNVERIFIED

| Step | Command | Result |
|---|---|---|
| Source table | DW MCP: `CREATE TABLE dbo.gate_fact (id INT NOT NULL, category VARCHAR(20) NOT NULL, amt DECIMAL(18,2) NOT NULL);` then `INSERT … VALUES (1,'A',10.00),(2,'A',20.00),(3,'B',30.00),(4,'C',40.00); SELECT category, SUM(amt) … GROUP BY category` | `A 30.00 / B 30.00 / C 40.00` (total **100.00**) |
| Create | `create_item` type `SemanticModel` `SM_Gate_Probe`, 5 parts: `definition/database.tmdl`, `definition/model.tmdl`, `definition/expressions.tmdl` (Direct Lake on OneLake: `AzureStorage.DataLake("https://onelake.dfs.fabric.microsoft.com/<ws>/<warehouseId>", [HierarchicalNavigation=true])` — the P24 shape), `definition/tables/Gate Fact.tmdl` (partition `mode: directLake`, `entityName: gate_fact`, `schemaName: dbo`, one measure `Total Amt = SUM('Gate Fact'[amt])`), `definition.pbism` (v4.0). CRLF on all `.tmdl` | 202 → LRO `36c8f4e1…` **Succeeded** (created 04:48:37, done 04:48:50 UTC, 13 s) → id `92deeba5-3447-421d-8bdd-a44125e80450` |
| Read back | `get_item_definition` | itself an LRO (`7b533322…`, Succeeded in <1 s) — definition read-back for SemanticModel is asynchronous, unlike MirroredDatabase |
| **Render check** (Chrome, view-only) | opened the Gate 4 report bound to this model | card shows **"Something's wrong with one or more fields."** → *Fields that need to be fixed*: **"Something's wrong with one or more fields or you don't have required permissions: (Gate Fact) Total Amt"**. The technical-details pane and the model's own page (`…/datasets/<id>/details`, which redirects to the canvas-only `modelView`) could not be read — the Chrome renderer timed out twice on `Page.captureScreenshot`; stopped per the rabbit-hole rule |

**Verdict: creatable and authorable through Core MCP; NOT yet proven to answer a query.** Definition
files kept on disk at `00_Plan/gate_probe/SM_Gate_Probe.SemanticModel/`.
**Leading hypothesis:** an API-created Direct Lake model has never been *framed* — no refresh has run
and there is no in-session refresh channel (REST unreachable; the Power BI remote MCP is not connected).
Alternatives: the OneLake path/`sourceLineageTag` shape for a Warehouse, or a missing model-level
Direct Lake annotation. **This is the first item of Session 2** (see `FINDINGS_S1.md` F-4); the
contract's §3 row 3 fallback (`.pbip` + one manual import) stays available.

---

## 5. Gate 4 — PBIR report via Core MCP — ✅ PASS (create) — first attempt rejected with useful errors

| Attempt | Command | Result |
|---|---|---|
| 1 | `create_item` type `Report` with hand-written `report.json` on schema **2.0.0** carrying `reportVersionAtImport` and `useNewFilterPaneExperience` | LRO `ec40c282…` **Failed** in 0.7 s: `Report_Import_FailedToImportReport` — *"Invalid type. Expected String but got Object. Path 'themeCollection.baseTheme.reportVersionAtImport'"* and *"Property 'useNewFilterPaneExperience' has not been defined and the schema does not allow additional properties"*. **The service validates PBIR against its JSON schemas and returns the JSON path** — a real validator, used as such |
| 2 | Same, with `report.json` / `pages.json` / `page.json` / `visual.json` copied from the delivered P26 report (`report 3.3.0`, `pagesMetadata 1.1.0`, `page 2.1.0`, `visualContainer 2.11.0`, base theme `Fluent2-CY26SU07`) and `definition.pbir` `byConnection` in P26's connection-string form (`Data Source=powerbi://api.powerbi.com/v1.0/myorg/<ws>;initial catalog=<model>;…;semanticmodelid=<id>`) | LRO `0669b05a…` **Succeeded** (04:51:56 → 04:51:58 UTC, 1.3 s) → id `c898faa9-7ab6-4642-9cdc-1d53450f1f8e` |
| Read back | report opened in Chrome at `/groups/<ws>/reports/<id>` | page `Gate` rendered with the card visual present (bound; data error is the Gate 3 finding, not a report finding) |

**Verdict: PASS.** The 2026-08 standing rule ("grep the most recent delivered project for `$schema`
versions … never hand-write shapes from memory", CLAUDE.md) was violated once and the service caught it
in under a second — the fastest lint this engine has ever had. Definition kept at
`00_Plan/gate_probe/RPT_Gate_Probe.Report/`.

---

## 6. Inventory count (App C 19)

Scratch workspace at its fullest (04:52 UTC `list_items`): **7 items** — Warehouse, SQLDatabase +
SQLEndpoint, MirroredDatabase + SQLEndpoint, SemanticModel, Report. Deleted with the workspace; 0 remain.

## 7. What changes in the contract (→ Rev 1)

| Row | Rev 0.2 expectation | Measured | Consequence |
|---|---|---|---|
| 1 Warehouse + DW MCP | UNPROBED | **PASS** with 12 controls | Channel row 13 stays [LIVE]; SETTLED row's "reopens when DDL/DML/EXEC gate fails" condition did not fire |
| 2 Open mirroring | UNPROBED | create/read-back **PASS** | replication test moves to §6 of the session (build-time) |
| 3 Semantic model via Core MCP | UNPROBED | create **PASS**, render **UNVERIFIED** | S2 opens with the framing question; fallback unchanged |
| 4 Report via Core MCP | UNPROBED | **PASS** | schema versions pinned to P26's |
| 7 SQL database | probe only | **FAIL** (analytics endpoint only) | dropped, no regret |

---

## 8. Build-time additions (recorded after the gates, same session)

The gates above ran 04:36–04:57 UTC. The build that followed established five more facts about the
same channels; they belong here because they are channel measurements, not build outcomes. Full
write-up with the commands in `FINDINGS_S1.md`.

| # | Fact | Established by |
|---|---|---|
| 1 | **The DW MCP gateway cuts the call at ≈ 100 s while the Warehouse keeps executing.** `EXEC eng.usp_run_range 4,13` → Cloudflare `502 origin_bad_gateway` at 09:03:43 UTC; a `SELECT COUNT(*)` 30 s later showed 12 days present, two of them written after the client gave up. Chunk long procedures to ≤ 6 days and re-read the progress table after any transport error — a 502 is not a rollback | the 502 body + `SELECT COUNT(*) FROM eng.attribution_daily` |
| 2 | **Four T-SQL shapes are rejected in distributed processing mode** — `CREATE SCHEMA` sharing a batch; DDL mixed with SELECTs on the dropped objects; a self-referencing `SET @x = (SELECT … > @x)`; a variable inside a JOIN predicate. Each has a one-line workaround, all four are in the delivered procedures | four error messages, each reproduced and then fixed statement-by-statement |
| 3 | **Fabric notebooks cannot be started by browser automation on this tenant** (two attempts): the ribbon is canvas-drawn (never in the accessibility tree), and the tab stops answering CDP after the coordinate click; the Monitoring hub showed no run. Reading pages by browser is proven; *acting on the Fabric canvas UI* is not | two Run-all attempts + Monitoring hub check at 10:11 UTC |
| 4 | **The built-in browser reads `bursamalaysia.com`, which both shells report as HTTP 000** — that is how the FCPO/FEPO rows became VERIFIED. It is **not** signed in to Fabric; Chrome is. Chrome for tenant UI, built-in browser for the open web | `Claude_Browser get_page_text` on both Bursa product pages |
| 5 | **Data through this channel is paid twice in tokens** (file read + tool argument): one 27 KB `INSERT` ≈ 105 k subagent tokens. The 25-batch load ran in 4 subagents; the main context never held a batch | subagent usage reports |

**Inventory at S1 close** (`list_items` on `WS_PalmDesk_Dev` `b06ab341-0860-4341-a6c9-5986d0d7f4b0`,
10:00 UTC): **5 items** — `WH_PalmDesk` (Warehouse), `VL_PalmDesk` (VariableLibrary),
`OMD_PalmDesk_Market` (MirroredDatabase) + its auto-provisioned `SQLEndpoint`,
`NB_PalmDesk_MarketFeed` (Notebook). Contract §3 expects exactly these at end of Phase 1, plus the
semantic model and report in S2.

---

# ADDENDUM — Session 2 (2026-09-06): §4 Gate 3 resolved to a verdict

**This supersedes the "Leading hypothesis" paragraph in §4 above.** That paragraph named *"never
framed"* as the leading hypothesis. **It is now disproven.** Full detail and the call-by-call table
are in `FINDINGS_S2.md` F-15; the summary and the commands are here because §4 is where the gate lives.

## What was run

| # | Command / action | Result |
|---|---|---|
| 1 | `mcp__Fabric_Core_MCP__create_item` — SemanticModel `SM_PalmDesk`, 14 parts, Direct Lake over `WH_PalmDesk`, same `AzureStorage.DataLake` shape as the S1 probe | **Succeeded** — LRO `79700813-2607-4d1b-ba9f-5c5fcda51c7a`, 11.2 s → item `f02c8481-f606-41b8-9026-b09ca1932258` |
| 2 | `update_item_definition` — 17 parts (12 tables, 108 columns, 13 relationships, 50 measures) | **Succeeded** — LRO `c0ff4038-bf5d-4f34-83fe-b247eccb2000`, 3.5 s |
| 3 | `create_item` — Report `RPT_PalmDesk_Check`, 11 parts, `byConnection` to the model | **Succeeded** — LRO `18281769-e0be-4a5f-b016-3501de4f879f`, 0.44 s → `31d7a0d6-149f-4b7d-b82c-33df6034daba` |
| 4 | Chrome: opened the report | All 4 data visuals error; the 2 textboxes render. **The S1 symptom reproduced on an independent model** |
| 5 | Chrome: *See details* → *See details* (the nested dialog S1's frozen renderer never reached) | **`Underlying Error: Missing_References`** · Activity `391ef543-3328-4041-bf72-aa728ffeb0a6` · Correlation `8a1a5082-626c-40af-7706-b0181f1817ea` · service `13.0.28514.444` · cluster `wabi-malaysia-west-a-primary-redirect.analysis.windows.net` · 2026-09-06 22:34:25 +08 |
| 6 | Chrome: **`Refresh now`** on the `SM_PalmDesk` row in the workspace item list — *the framing test* | Clicked and fired; the row's Refreshed stamp populated |
| 7 | Chrome: re-opened the report in a **fresh tab** (the first tab's renderer froze — F-18/§132 pattern) | **`Missing_References` again, unchanged** |
| 8 | `get_item_definition` on the model, decoded | Definition intact and complete: 12 `ref table` lines, 13 relationships, 50 measures. **The definition is stored correctly; it is the resolution that fails** |

## Verdict

**Gate 3 = CREATABLE, UPDATABLE, READABLE-BACK — DOES NOT ANSWER. Framing is not the cause.**

A refresh ran and changed nothing, so the S1 hypothesis (a) is closed negatively. The remaining
hypotheses are unranked by evidence:
- **(b)** the Direct Lake binding shape differs for a **Warehouse** — note that both of this engine's
  failures are Warehouses, while P24's proof was a **Lakehouse**;
- **(c)** a missing model-level Direct Lake annotation;
- **(d)** new this session — the engine has only ever submitted `definition.pbism` **`4.0`** with
  `compatibilityLevel` **`1606`**, while Core MCP's own `get_knowledge` documents **`5.0` / `1702`**
  today. The re-push carrying that change **failed on payload transcription (F-17), not on the
  tenant**, so this is untested and cheap to test.

**The one read that would settle (b) and (c) together** is a portal-created Direct Lake model over
the same Warehouse, then `get_item_definition` on it — the service's own shape, for this tenant, for
a Warehouse. It was attempted and blocked: the affordance is in the Warehouse ribbon, which is
canvas-drawn and absent from the accessibility tree (F-18). **It needs one human click and it is the
first item of Session 3.**

## Consequence taken

Contract §3 row 3's fallback was **executed in the session the gate failed**, per the standing rule:
`06_Report/P27_PalmDesk_pbip/` is a complete `.pbip` — the same TMDL plus the 4-page report bound
`byPath` — that opens in Desktop with one import. No work was left stranded on the failed route:
the model, the measures and the report are the same artefacts either way.

---

# ADDENDUM 2 — Session 2, post-close (2026-09-06): five hypotheses eliminated

Run on the user's instruction to proceed after the close ritual. Full detail: `FINDINGS_S2.md` F-24.
Probe definitions kept at `00_Plan/probe_s2/`.

| Hypothesis | Verdict | What was run |
|---|---|---|
| (a) never framed | **eliminated** | Portal `Refresh now`; render unchanged (Addendum 1, step 6-7) |
| model size / complexity | **eliminated** | 1-, 2- and 12-table models fail identically |
| (d) `pbism.version` skew | **eliminated — and provably untestable** | Submitted `4.0` → stored `4.2`; submitted `5.0` → stored `4.2`. Two inputs, one output: the service overwrites the field |
| `compatibilityLevel` | **eliminated as the cause** | It IS honoured (1702 submitted, 1702 stored) — and 1606 and 1702 both fail |
| (b′) name-form OneLake path | **eliminated** | Probe C rejected **at create**: *"Direct Lake mode requires a Direct Lake data source. Tables in Direct Lake mode must be the SQL or OneLake datasource kind…"* |
| (e) unbound cloud connection | **eliminated** | Settings pane shows the source recognised (`AzureDataLakeStorage{…<ONELAKE-HOST>…}`) and mapped to *Default: Single Sign-On (Entra ID)*; clicked **Apply** to commit it, re-rendered — unchanged |

**The narrowing that matters:** Probe C proves the service **validates the Direct Lake datasource
kind at create time**, and it **accepts** our GUID path. The source is therefore correct; the
**table binding** is what fails at query time. Leading hypothesis **(f)**: `sourceLineageTag` must
carry the service's own delta-table identifier, not the synthesised `[schema].[table]` string this
engine writes — which fits `Missing_References` on every field of every table while the datasource
validates clean.

**(f) cannot be tested by guessing**, because the value in question is the service's, not ours. The
portal comparator is now not merely the cheapest route — it is the only one.

---

# ADDENDUM 3 — Session 2, 2026-09-07: Gate 3 PASSES

**Gate 3 is now ✅ PASS — creatable, updatable, readable back, AND it answers.** Detail: `FINDINGS_S2.md` F-29.

| # | Action | Result |
|---|---|---|
| 1 | Probe: swap `AzureStorage.DataLake(...)` for `Sql.Database("<endpoint>", "43516adb-…")` — one variable | Succeeded, LRO `e3badce0-…`, 2.9 s |
| 2 | `Refresh now`, re-render `RPT_Probe_A` | **Renders.** Dates 2026-03-16 onward, measure **−168,329.67** = Warehouse truth exactly |
| 3 | Same swap on the real `SM_PalmDesk` (17 parts, 53,864 B base64) | Succeeded, LRO `fefed879-…`, 4.4 s, first attempt |
| 4 | `Refresh now`, render `RPT_PalmDesk_Check` | **14 of 14 measures match Warehouse truth**; residual **0.00**; zero-relationship probe **passes** |
| 5 | Deploy + render `P27_PalmDesk_Smoke` (Position + Attribution, every visual type) | **All render clean**, waterfall and `mkt`-schema card included |

**Why the OneLake form failed silently:** it is a legal Direct Lake datasource kind, so the service
accepts it at create (Probe C proved the validator checks kind); the metadata loads and the modeling
canvas draws it. It simply never binds a Warehouse's tables. Nothing in the create path, the
read-back, `validate_pbip.py` or the PBIR schema validator can see that — **only a rendered value can.**

**Both prior "fixes" stay, and neither was the cause.** Bare `sourceLineageTag` and the dropped
`[HierarchicalNavigation=true]` were each pushed, refreshed and rendered on their own; both still
failed. They are correct per the documentation and are kept on those grounds alone.
