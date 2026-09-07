# How to put this on GitHub

**This folder is the repository, complete and verified.** It is not committed anywhere: this session
could not create the repo, and the reason is measured rather than assumed — see
`_probe/PROBE_GITHUB_20260907T0900Z.txt` in the engine root. In short: the cloud session is
**repository-bound** by the agent proxy, so account-level endpoints (which is where repo creation
lives) return 403 by design, there is no `gh` CLI, and git credential injection does not extend to
arbitrary remotes. It failed in four ways with a negative control, so it is settled, not flaky.

**Verified before hand-off** (`check_rebuild_materials.py --allow scrub_allowlist.txt`):

```
files in repo   : 155  (61 runnable rebuild artefacts)
scrub           : 0 BLOCK instance(s)
ALL REBUILD MATERIALS PRESENT, NON-EMPTY AND SCRUBBED
```

Suggested repo name — matches the P25/P26 pattern: **`palmdesk-ctrm-fabric`**
(the README, the guide and the deck all already point at
`github.com/BIVenture2025/palmdesk-ctrm-fabric`; if you choose a different name, change it in
`06_Portfolio/_build_guide.py` and `_build_deck.js` and regenerate, rather than hand-editing the
outputs).

---

## The five traps, all hit on earlier projects in this series

| Trap | What happens | What to do |
|---|---|---|
| **Dotfiles cannot be uploaded** | Drag-and-drop and the file picker both silently skip `.gitignore` and `.nojekyll`. GitHub says *"Add some files to include in this commit"* with nothing attached | **Add file → Create new file**, and type the name including the leading dot. Both files in this folder need this |
| **Empty repo has no `main` branch** | `/upload/main` redirects back to the repo page | Use **`/upload`** for the very first commit only |
| **GitHub does not render `.html`** | A link to `docs/guide.html` shows raw markup to every visitor | **Enable GitHub Pages**, and make the README's guide link **absolute** to the Pages URL so it works from both views |
| **Jekyll breaks the Pages build** | Pages runs Jekyll by default; any `{{` or `{%` in a `.md` file is read as a template variable and the build **fails**. This repo contains Power Query M, f-strings and DAX — all of which contain `{{` | The **`.nojekyll`** file at the repo root prevents it. It is in this folder; make sure it actually uploads (see the dotfile trap) |
| **Uploading into a subfolder** | Dragging onto the root upload page creates a duplicate at root instead of replacing the file | Navigate into the folder first, or use `/upload/main/<path>` |

**Same-path uploads overwrite.** Nothing needs deleting to update a file — the commit shows as a
modification, which is the confirmation that the path matched.

---

## Order

1. Create the repository (public, no README — this folder has one).
2. `/upload` — drag everything **except** the two dotfiles.
3. **Add file → Create new file** ×2 for `.nojekyll` and `.gitignore`.
4. **Settings → Pages** → deploy from `main`, root.
5. Open `docs/guide.html` at the Pages URL and click both repository links in it. They were **not**
   fetched by the checker — it has no egress — so they are the one thing still unverified.
6. Tell me the Pages URL and I will finish the portfolio card
   (`06_Portfolio/CARD_COPY_AND_BLOCKER.md` has the copy ready and explains what is still blocked).

---

## What was redacted, and what deliberately was not

`scrub_check.py` found **6 real BLOCK instances** in this folder — five Fabric SQL endpoint
hostnames and one OneLake endpoint. **All six were redacted in the files themselves, not
allowlisted**, per the tool's standing rule that an endpoint is redacted unconditionally. A note at
the redaction site in `model/expressions.tmdl` explains what was removed.

**The connector shape was deliberately kept.** That one line is the project's central finding, and
redacting it would have destroyed the thing worth publishing.

**260 GUIDs remain, on purpose.** Every one is trial-scoped — the capacity expires around
2026-10-03, taking the workspace, warehouse, model, report and mirrored database with it. They are
also load-bearing evidence: the item ids are what make "all four pages render against Warehouse
truth" and "9 items reconciling to the contract" checkable rather than asserted. They are WARN, not
BLOCK, and are reported for confirmation rather than suppressed. The reasoning is written out in
`scrub_allowlist.txt`, which is deliberately almost empty — it contains one entry, the contact
address published on purpose in the README sign-off.
