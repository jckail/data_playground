# Standalone Data Playground bounded repair review

Release base: `origin/main` at `289094d`, which contains merged architecture PR #2 and has the same tree as the earlier `52a2a6a` source worktree. Isolated edits live in `/home/jkail/data-playground-superdesign-fixes`, branch `fix/standalone-audit-ui`. No changes to existing owner worktree or canonical dirty checkout. Supported `playground/` engine/service is preserved. This repair is prepared for release; deployment state must be established from the final CI and target verification.

## Audit resolution

| Finding | Resolution and practical limit |
|---|---|
| D1 missing generated Jinja fragments | Actual template now falls back to tracked chart-unavailable.html; missing and mixed-present fragments rendered offline. No fake chart values added to production. |
| D2 synchronous Session awaited | Health and rollup handlers now synchronous, annotated Session, invoking sync execute. Rollup404 retained instead of remapped500. Other legacy model/task sync/async mismatches are outside scope and remain unverified. |
| D3 shop trace dates from users | Shops have their own queried x-values. Partial user/shop series survives; offline regression covers mismatched/empty user dates. |
| D4 SQL failure shown as no data | Query retries propagate terminal error; chart functions propagate, Streamlit gather emits generic failure. No database invoked. |
| D5 host0.0.0.0 URLs | Same-origin tool paths, `/streamlit/` matches Nginx. Canvas uses inert hash links and disabled controls. |
| D6 queued actions/status | Accessible status, pending disable/duplicate guard, HTTP failure, network ambiguity and timeout. Does not claim completion or refresh. Three actual source-script jsdom request states verified. No endpoint invoked. |
| D7 mobile header overlap | Flow-layout wrapping flex nav replaces fixed floats. Content follows nav;44px controls and mobile CSS. Browser layout not verified. |
| D8 missing document structure | Doctype, language, charset, viewport/title, nav/main/sections, h1, aria labels and status. |
| D9 exception detail exposed | Streamlit UI generic, detailed traceback in application logs. No exception values echoed to UI. Health/rollup error text generic too. |
| D10 last-hour misleading | Latest recorded hour label and actual returned min/max interval caption; historical nature explicit. Query meaning preserved. |
| D11 README service mismatch | New supported README had already distinguished service8010 vs legacy. Added exact legacy gateway8000/internalStreamlit8501/no activeGrafana service and bounded repair limits. |

## Verification

- 5 focused offline unittest cases passed (system Python includes Jinja2); no app module import or database connection.
- 3 jsdom interaction states passed; concurrent second submission blocked while first pending.
- Ruff checks on new regression tests passed.
- Six changed Python source files parsed successfully; `git diff --check` passed.
- No full test/build/dependency install scheduled, so no shared expensive verification lock contention.
- CLI authenticated preflight; home and Streamlit same draft IDs now version2, review guide version3, AnalyticsNavbar component version2. Zero import warnings. Every saved HTML refetched and byte compared; all saved fingerprints current.

## Design association and supported source

Same standalone project455b1495-879c-4308-8228-7c12040fa5a2. Canonical association migrated to `/home/jkail/projects/data_playground`; reviewWorktree records isolated source edits. Existing home/Streamlit remain explicitly legacy.52a2a6a adds headless API endpoints, deterministic pipeline/catalog, graph/features and architecture replay. The supported frontend lives in Portfolio; no standalone invented UI added.

Legacy Plotly/SQLAlchemy/Streamlit dependencies unavailable in existing environments; DB, scheduler, live API/browser rendering remain unverified. Broader legacy DB operations still await synchronous sessions and are not certified functional. Agent Hub context refused native canonical repository selection; local evidence saved here rather than uploading against an inferred project. Root owns shared Graphify refresh. Graphify query returned unrelated repositories; coverage gap handled via current targeted source inspection.

## Release verification additions

The focused `legacy-presentation` CI job installs an isolated pinned verification
environment. It imports the actual Plotly chart module, asynchronous query module
and FastAPI rollup router while replacing only database and outbound HTTP
boundaries. It checks independent chart dates, terminal query failure after
retries, preserved 404 and the two queued rollup tasks without making network
calls or starting the legacy application. Jinja tests also run with real runtime
dependencies in that job. The original supported-lab CI continues to run the full
engine/API/architecture suite, Ruff and two byte-identical catalog exports.

The repository has no hosted deployment workflow or production destination.
`compose.lab.yml` is a documented local loopback service, not evidence of hosted
deployment. The original legacy gateway must not replace another application's
occupied port 8000. No legacy fake-data scheduler or mutation job is run by these
checks.
