# Continue here — implementation checkpoint

## Latest user steering: TokenRouter and deployment

The user has now authorized using their provided test API key with `https://api.tokenrouter.com/v1` and **`z-ai/glm-5.3-free`**, and wants a publicly usable deployed website. A real call through the current adapter succeeded with `{"available":true}` (97 tokens, approximately 7.9 seconds). The credential is in gitignored `.env` with filesystem mode 0600, never in this document or frontend code. The adapter now selects `/chat/completions` when FACT_API_KEY is nonempty. Existing results are still from gpt-oss; rerun the selected pilot with TokenRouter and evaluate before scaling. Deployment is now requested, but no hosting target or remote deployment exists yet. Preserve the local key and configure it as a server-side hosting secret. Do not expose it through a static site bundle. The original form submission still has not been requested explicitly.

The user pasted the same new instructions twice. They are steering the same assignment, not two separate projects. The source handoff's planning-only language is superseded by explicit authorization to implement.

The user authorized implementation and asked for a handoff near the Codex quota boundary. At the last usage check, 89% of the five-hour allowance was consumed. This is a working foundation, **not a finished assignment**. Do not claim otherwise.

## Current state

- Python API, React UI, SQLite/FTS5 storage, background worker with leases, upload validation/deduplication, page/region parsing, exact source highlighting, typed claims, model extraction and a second model verification pass are implemented.
- `make setup`, `make dev`, `make test`, `make ingest`, `make export-samples` exist. API/UI use **127.0.0.1:8017**; another unrelated user process occupies port 8000. Do not kill it.
- The API was started on 8017. The worker was deliberately stopped after jobs settled so no further model usage occurs unattended. Start with `make dev` after checking whether 8017 is already occupied by this app; or start only the worker if the API is already running.
- Ollama was started on 11434. Existing account access to `gpt-oss:120b-cloud` worked. `glm-5:cloud` returned 410 and `glm-5.1:cloud` returned 402. Only tiny cloud manifests were pulled, no local model weights. No paid upgrade or account changes were made.
- 29 controlled automated tests passed. Frontend TypeScript/Vite build passed. PyMuPDF/Starlette emit dependency deprecation warnings.
- A browser opened the UI successfully and produced a DOM snapshot. One console error needs inspection (likely favicon but NOT verified). The screenshot attempt failed because the output directory did not yet exist. Full visual/keyboard/mobile verification is unfinished. Impeccable's mechanical detector ran once and returned no findings.

## Data and actual results

- `data/knowledge.sqlite` is the current development DB; `data/pdfs/` contains all source PDFs addressed by SHA-256. `data/pilot-v1.sqlite` is an earlier backup. All are gitignored.
- Six documents / 511 pages parsed. The selected pilot has 15 PDF pages (20 region extraction requests plus verification in the second run). Most jobs intentionally show partial status; the annual-report job showed failed because relationship insertion had seven placeholders for a six-column table. That SQL bug has been fixed but its persisted job status has not been reset/re-run.
- After the latest safety audit: **52 accepted claims, 114 quarantined candidates**. Accepted does not imply manually proven correctness. These 52 still require evaluation. No validated relationship demonstration is complete.
- `samples/evaluation/pilot-v1-failures.json` preserves real early failures, including PTL chart misassociation and wrong subject attribution.
- `samples/actual-runs/*.json` are genuine exports of current partial results, page text/coordinates, runs, and failures. They contain no invented sample facts. Importing them into a portable saved-results mode is NOT implemented.
- Model calls and prompts are versioned in `runs`. The latest prompt/guards were edited after the second pilot; the complete pilot has NOT been rerun with all latest improvements.

## Highest-priority work (do this before full-corpus processing)

1. **Fix extraction correctness.** The model accepted bogus table associations even in the verifier pass. Native block ordering can still misread infographics and some columns. New generic guards quarantine infographic numbers (large numeric display spans), unsupported scope strings and quarter qualifiers dropped from period. More meaningful source-to-subject and value-to-column validation is needed; use PyMuPDF table cells/coordinates or a vision-capable accessible model for hard layouts. Do not patch particular company names or values.
2. **Repair context extraction.** The model invented `scope=standalone` from headings such as “Key operating metrics,” including for macroeconomic facts. The new exact scope-evidence guard quarantines this, but better extraction should omit unsupported fields. The updated prompt requests verbatim time context and optional scope. Main issuer identity comes from first-three-page reference units; still check pronoun attribution to issuer versus nearby subsidiary headings.
3. **Reprocess selected pages cleanly with a new pipeline version.** Existing `pages.status='extracted'` checkpoints skip those pages, and content duplicate uploads reuse jobs. Add a proper version-aware reprocess command; preserve old claims/runs as superseded. Bumping the version only invalidates model cache; it currently does not invalidate page checkpoints. Avoid duplicate or stale relationships. Stable claim IDs reduce identical rerun duplication but do not solve changed outputs.
4. **Finish and evaluate relationships.** `alignment.py` and `scripts/reconcile.py` were written but not run/validated. They discover predicate aliases then use deterministic comparison or model judgment on unresolved pairs. Integrate into the worker after validating; currently only deterministic comparisons run automatically. Add tests for persisted relationship insertion, alias effects, invalidation and cross-document retrieval. Model numeric judgments need deterministic arithmetic revalidation. Fiscal/calendar and estimate-vintage normalization need careful source support.
5. Reproduce the four cases in ANALYSIS_AND_AGENT_HANDOFF.md through runtime extraction: PIN coverage corroboration; corporate postal-code discrepancy (122002 vs 122001); scope/unit/vintage reconciliation; observed chart extraction failure. Expected values belong in evaluation fixtures only. Some currently quarantined address claims are otherwise correct but carried invented scope; rerun rather than manually seed corrected facts.

## Other missing engineering work

- Bounded model accounting currently undercounts retries/repair/verifier calls and allows the last call to exceed budgets. Alignment/judgment budgets are not wired to jobs. Fix before all-511-page extraction.
- Page retries can retain partial-region claims and stale failures; make region checkpoints/versioning explicit. Worker ownership must be rechecked on writes if a lease is lost. Add cancellation if retaining that promised job state.
- Coordinate extraction is native-text only. `FACT_ENABLE_OCR` exists but is not implemented; remove or implement it. Rotation mapping needs a real rotated-PDF test. Existing word boxes use unrotated coordinates while rendered dimensions may be rotated.
- `ClaimDetail` currently combines context anchors from other pages onto the primary page SVG. Fix by grouping evidence by page, showing context-page links, and filtering overlays to the displayed page. Add dialog focus trap/restore and verify Escape behavior.
- API health currently always says `mode=live`; UI has saved-mode handling but no backend mode/import. Implement hash-verified import of genuine exports and disable live upload in saved mode.
- Set retrieval/registry endpoints and filters only if useful; do not add a graph, chat, authentication, or cloud hosting before core correctness.
- Add evaluation fixtures with 30–40 manually verified claims and 15–20 pairs; current tests are controlled synthetic unit/integration checks, not corpus accuracy. Report misses and abstentions separately.
- Fresh-install run through README, mobile/desktop source viewer verification, actual sub-three-minute demo recording, final source exports and GitHub/video publication remain. No remote repository, video, form submission or hosted deployment exists. Publication/form authorization is still separate.

## Commands and files

```sh
uv run pytest -q
uv run ruff check backend scripts tests
npm run build --prefix frontend
uv run python -m backend.factlayer.worker
uv run python -m scripts.reconcile
uv run python -m scripts.export_samples
```

Model/grounding: `backend/factlayer/model.py`, `pdf.py`, `schema.py`.
Jobs/DB: `worker.py`, `db.py`, `ingest.py`.
Relations: `compare.py`, `alignment.py`.
Interface: `frontend/src/App.tsx`, `style.css`.
Tests: `tests/`; sample selection: `scripts/ingest_starters.py`.

Use the approved ANALYSIS_AND_AGENT_HANDOFF.md as the target contract, README.md as actual current capabilities, and this file as the gap list. Continue independently through local work; do not treat passing synthetic tests as permission to claim the assignment is finished.
