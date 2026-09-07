# FINDINGS — Project 27, Session 1 (2026-09-06)

Drafted per the kickoff's step 9. Each row names **what was run** to establish it (App C 18) and where it
dual-writes. Rows marked **→ CHANNELS** belong in `_ENGINE/reference/FABRIC_AUTOMATION_CHANNELS.md`;
**→ SETTLED** in `_ENGINE/reference/SETTLED.md`; **→ GUIDE** are build lessons for
`PBIP_GENERATION_GUIDE.md` + the CORE_RULES fold.

---

## F-1 — DW MCP executes DDL, DML, EXEC, views and multi-statement batches → CHANNELS row 13, SETTLED

Gate 1, 12 controls, all in `00_Plan/Gate_Check_Results.md` §1 with verbatim statements. Positive:
`CREATE TABLE`, `INSERT`, `SELECT`, `CREATE PROCEDURE`, `EXEC` (result set returned through the tool),
`UPDATE`+`DELETE`+`SELECT` in one call, a **1,000-row / 27,051-byte single `INSERT`**, `CREATE VIEW`,
`INFORMATION_SCHEMA`, `DROP`×3. Negative: an invalid object name and a syntax error both returned
`-32002` **SQL** errors carrying the engine's own message.

**Verdict: the SETTLED row's reopen condition ("DDL/DML/EXEC gate fails in P27 S1") did NOT fire.**
Row 13 upgrades from "read half proven" to **fully proven**, with the S1 build as the evidence:
5,919 source rows loaded, 5 procedures created, 124 `EXEC`s run, 400 aggregate rows reconciled.

## F-2 — The DW MCP gateway cuts the CALL at ≈ 100 s; the Warehouse keeps executing → CHANNELS, SETTLED

`EXEC eng.usp_run_range @from_idx = 4, @to_idx = 13` (10 business days) returned
**HTTP 502 `origin_bad_gateway` from Cloudflare at 09:03:43 UTC**, ~105 s after the call. A `SELECT COUNT(*)`
30 s later showed **12 days present** — the procedure had run past the point where the client gave up, and
the two extra days landed after the 502. A second 502 at 09:07:27 behaved the same way (27 days present
after the failed call reported nothing).

**Rule for every long procedure on this channel:** chunk to ≤ 6 business days per call, and after ANY
transport error **re-read the progress table** (`eng.run_log` / `MAX(biz_date)`) before re-issuing — a
502 is not a rollback. The 120-day run finished in 20 chunks with zero duplicate work because
`usp_run_eod` deletes its own day first (idempotent by construction — build every such procedure that way).

## F-3 — Fabric Warehouse "distributed processing mode" rejects four T-SQL shapes → GUIDE + CHANNELS

All four were hit and fixed live; each is a one-line workaround, and none is documented in an obvious place.

| # | Shape that fails | Exact error | Workaround (used in `02_Platform/WH_PalmDesk.Warehouse/`) |
|---|---|---|---|
| a | `CREATE SCHEMA` with anything else in the batch | `Incorrect syntax near the keyword 'CREATE'` | one `CREATE SCHEMA` per call (five calls) |
| b | A batch mixing DDL with SELECTs that read the objects being dropped | `The query references an object that is not supported in distributed processing mode` | DDL-only batches; the SELECTs alone and the DROPs alone both succeed |
| c | Self-referencing variable assignment: `SET @me = (SELECT MIN(x) FROM t WHERE x > @me)` | `Queries referencing variables are not supported in distributed processing mode` | stage through a second variable: `SET @next = (SELECT …); SET @me = @next;` |
| d | A variable inside a JOIN predicate: `JOIN … ON c.curve_date = CASE WHEN @me < w.closeout THEN @me ELSE w.closeout END` | same message as (c) | write the value into a work-table column first (`UPDATE eng.w_hedge SET price_date = CASE WHEN @me < closeout …`), then join on the column |

**The message in (c)/(d) names the symptom, not the shape** — "referencing variables" is true of a hundred
working statements in the same procedure. The way to locate it is to run the procedure body statement by
statement in one ad-hoc call each; both were found in two calls that way.

*Not tested:* `UPDATE <two-part name> SET … FROM <same table> <alias> JOIN …`. Every `UPDATE … FROM` in the
delivered procedures is written as `UPDATE <alias> SET …` pre-emptively; whether the two-name form also
works is **unknown and was not measured** — do not record it as unsupported.

## F-4 — A SQL database in Fabric is reachable through the DW MCP only as its read-only analytics endpoint → SETTLED

Gate 7. `create_item` type `SQLDatabase` succeeded (24 s) and auto-provisioned a companion `SQLEndpoint`.
`execute_query` against **either id** returns `@@VERSION` = *"Microsoft Azure SQL Data Warehouse (RTM) —
12.0.2000.8"* and `SERVERPROPERTY('EngineEdition')` = **11**, i.e. the Fabric analytics endpoint, never the
OLTP database. Reads work; `CREATE TABLE` returns
`The external policy action 'Microsoft.Sql/Sqlservers/Databases/Schemas/Tables/Create' was denied`.
(With a `PRIMARY KEY` clause it fails earlier and differently: *"The PRIMARY KEY keyword is not supported
in the CREATE TABLE statement in this edition of SQL Server"* — a red herring; the policy denial is the
real answer.) **Component dropped, no regret.** This closes the "unknown" in channels doc §2i.

## F-5 — A Direct Lake semantic model created by API does not answer a query (open) → S2 item 1

Gate 3. `create_item` type `SemanticModel` with 5 TMDL parts (P24's `AzureStorage.DataLake` expression
shape, `mode: directLake`, CRLF) **succeeded** (13 s LRO) and the definition read back. The bound report's
card shows *"Something's wrong with one or more fields or you don't have required permissions:
(Gate Fact) Total Amt"*. Leading hypothesis: **the model has never been framed** — no refresh has run and
this session has no in-session refresh channel (REST unreachable; the Power BI remote MCP is not connected).
Alternatives not yet excluded: the OneLake path/`sourceLineageTag` shape for a **Warehouse** (P24's proven
example was a **Lakehouse**), or a missing model-level Direct Lake annotation.
**Do not conclude "Core MCP cannot author Direct Lake models" from this** — creatability is proven; only
answering is not.

## F-6 — The Report service-side PBIR validator is the fastest lint this engine has → GUIDE

A hand-written `report.json` on schema 2.0.0 was rejected in **0.7 s** with two JSON paths:
*"Invalid type. Expected String but got Object. Path 'themeCollection.baseTheme.reportVersionAtImport'"* and
*"Property 'useNewFilterPaneExperience' has not been defined and the schema does not allow additional
properties."* Copying P26's delivered `report.json` / `pages.json` / `page.json` / `visual.json` versions
(report 3.3.0, pagesMetadata 1.1.0, page 2.1.0, visualContainer 2.11.0) passed in 1.3 s.
**The standing rule "grep the most recent delivered project for `$schema` versions, never hand-write from
memory" now has a cheap enforcement mechanism: send it and read the JSON path.**

## F-7 — Data volume through the DW MCP is paid twice in tokens → GUIDE (cost)

One 27 KB `INSERT` cost a subagent ≈ 105 k tokens (the file is read AND re-emitted as the tool argument).
The 25-batch load ran in **4 subagents** for exactly this reason; the main context never held a batch.
Measured this session: 86 `execute_query` calls, 9 subagent transcripts, 14.2 M subagent cache-read.
**Rule: any load > ~50 KB total goes to subagents, one table group each, verified by count + checksum in
the subagent's own final message.**

## F-8 — Browser automation could not start the notebook run (open) → CHANNELS caveat

Two attempts, fresh tab each, window resized to 1600×1000, `?experience=fabric-developer`: the notebook
canvas rendered (code visible, "Not connected", 6 cells), the click at the **Run all** ribbon position was
delivered, and the tab then stopped responding to CDP —
`Page.captureScreenshot timed out after 30000 ms` on every subsequent call. The Monitoring hub (a
different tab, working normally) showed **no NB_PalmDesk_MarketFeed activity** afterwards, so no run
started. `find` never located a "Run all" element in the accessibility tree at any point: the Fabric
notebook ribbon appears to be canvas-drawn, so only coordinate clicks are possible, and their target
cannot be verified before clicking.
**Consequence for the channel ladder:** "browser automation can click Run" is **not established** for
Fabric notebooks on this tenant. It worked for reading pages (banner, Bursa, report render, monitoring
hub) — reading is proven, *acting on a canvas UI* is not. The kill route (feed as Warehouse tables) was
already in force, so nothing was blocked.

## F-9 — The built-in browser reaches bursamalaysia.com, which neither shell can → CHANNELS

The channels doc records `bursamalaysia.com` as HTTP 000 from the device VM, and every fetch path failed in
the planning session. The **built-in browser pane read both product pages in full** (FCPO and FEPO,
`get_page_text`), which is how `TERMINOLOGY.md` moved from SECONDARY to VERIFIED.
**Rule: a site that refuses WebFetch and both shells is not unreachable — try the built-in browser before
recording it as blocked.** Also measured: the built-in browser is **not signed in to Fabric** (it landed on
the sign-in email form), while Claude-in-Chrome is. Use Chrome for tenant UI, the built-in browser for the
open web.

## F-10 — Channel inventory on the day → CHANNELS

`RefreshMcpTools` 04:35 UTC: **Fabric Core MCP = 29 tools** (unchanged since 2026-08-26 — still no OneLake,
job-run, connections, Git or deployment-pipeline tools), **Fabric DW MCP = 1 tool** (`execute_query`).
Fabric REST / `fab` / `az` / OneLake: not re-probed this session; the 2026-09-06 SETTLED row stands and its
consequence (MCP + browser only) shaped every step above.

## F-11 — A tolerance-based checksum hid a precision loss that changed a statistic → GUIDE + a lint candidate

`mkt.monthly_history.price` was created `DECIMAL(12,2)` while the generator emits 6 dp. The load's
verification reported **MATCH** — because the check was "within ±0.50 of 144713.608637", a tolerance I
wrote into the subagent's instructions to absorb the very rounding that was the bug. The truncation then
changed the hedge regression's **R² from 0.8555 to 0.8498** and the slope from −1.0132 to −1.0131.
Nothing broke: relationship 5 fails on the dollar-offset test, not the R² gate. **But 0.8498 is 0.0498
above the 0.80 prospective threshold — a slightly different seed and the truncation would have flipped a
hedge from effective to ineffective, with a green checksum.**
Fixed by `DROP`/`CREATE` at `DECIMAL(12,6)` and a reload; the T-SQL and replay then agreed on all 480
hedge fields.
**Rules:** (1) a checksum with a tolerance is not a checksum — compare the SQL `SUM` at the column's full
precision, and if the two cannot match exactly, the column type is wrong; (2) every source column that
feeds a **statistic** (regression, ratio, rate) carries the generator's precision, not the display
precision. Lint candidate for `validate_pbip.py`'s family: flag a generator column whose emitted decimals
exceed its DDL scale.

## F-12 — Reconciliation shape that proved the engines → GUIDE

Two independent implementations (T-SQL in the Warehouse, pandas in the container), same docstring, compared
as **aggregates over the full run** rather than spot checks: attribution by day (12 fields × 120),
MTM by day (n, Σmtm, Σ|mtm|, Σqty × 120), exposure by day (Σexposure, Σecl, n_breach × 120), exposure by
counterparty (Σexposure, Σutil, n_breach, first_breach × 40) = **400 rows, 0 mismatching fields**, plus
**40 hedge rows × 12 fields = 480, 0 mismatches** after F-11. Decimal equality, never float.
The reconciler is `03_Engines/reconcile.py` and it prints rows-compared, so a zero-mismatch result cannot
be confused with a zero-rows result (App C 24).

## F-13 — The credit-limit RULE was changed after seeing results; the THRESHOLDS were not → contract §5, honesty note

First limit assignment (grade-based, MYR 5–30 m for everyone) put **24 of 40 counterparties in breach** —
not a credible book, and it would have buried the two engineered names in noise. The **rule** was rewritten
uniformly — buyers carry cargo-scale limits (a delivered cargo before payment is full-value exposure:
A 150 / B 110 / C 75 / D 40 m × a size factor), suppliers replacement-cost limits (A 25 / B 15 / C 8 / D 4 m)
— and re-derived limits were applied to every counterparty including the engineered two (CP 3 → 12.0 m,
CP 18 → 90.0 m, both from the rule, neither hand-set). Result: **6 breaches — the 2 engineered plus 4
organic**, which are kept and labelled organic.
**The graded thresholds (75 % amber / 90 % red / 100 % breach) and the unexplained tolerance were never
touched.** Recording this because "thresholds never tuned to the injected truth" is a contract term and the
distinction between *tuning a threshold* and *fixing an implausible data rule* is exactly where that term
gets quietly broken.

## F-14 — Two generator bugs the replay caught before the tenant did → GUIDE (method)

(a) Futures were booked into contract months whose close-out (last business day of the preceding month) had
already passed, so the replay raised `KeyError: '2026-04'` on day 1 — the T-SQL would have produced
silently wrong positions. (b) `add_months` had no negative-month branch, so computing a close-out for a
January contract raised `ValueError: month must be in 1..12`.
**Both were found by the offline replay, not by the Warehouse**, which is the case for building the second
implementation *before* trusting the first (P24 rule) — and for running the replay on the same CSVs that
produce the SQL batches, so a generator change is caught by a diff of the CSVs rather than by a reload.
