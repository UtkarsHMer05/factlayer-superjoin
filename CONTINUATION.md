# Continue the Superjoin assignment

Updated September 8, 2026. **Implementation is authorized. This is not a planning-only task.** The user asks to finish the assignment and deploy a working website judges can use. Do not ask again whether to implement. Do not submit the hiring form without specific submission authorization.

## Immediate state

Project: `/Users/utkarshkhajuria/Desktop/SUPERJOIN ASSINGMENT`.

Read this file, README.md, DEPLOYMENT.md, then ANALYSIS_AND_AGENT_HANDOFF.md and the original assignment PDF. The latter analysis contains exact requirements, source-page discoveries, and the intended four-case demo. Facts mentioned in documentation are evaluation expectations, NEVER runtime seed answers.

The user supplied a TokenRouter key. It is already in ignored `.env` with chmod 0600. Do not print it, put it in VITE variables, commit it, or ask for it again. Exact requested model: `z-ai/glm-5.3-free`; endpoint: `https://api.tokenrouter.com/v1`. The key is authorized for this project. No silent switch to another model. An earlier tiny request returned valid JSON (97 tokens, ~8s); later tiny and full extraction requests timed out or stayed pending. A 45-second diagnostic with low effort timed out. Full requests were interrupted during handoff after retries; do not claim they completed.

The model adapter sends GLM's documented top-level `thinking: {"type":"disabled"}` and a configurable `max_tokens` limit. It uses a configurable streaming-idle timeout (45 seconds by default), stops on read timeouts instead of retrying them three times, and retries other transient/invalid-JSON failures at most three times. A fresh bounded smoke request after this change reached TokenRouter immediately but returned HTTP 429; do not keep retrying while quota is rate-limited. API keys are kept only in Authorization headers.

There is no authenticated hosting destination yet. An async question asked whether the user will provide Render, another host, or wants the local handoff first. No answer had arrived at this checkpoint. Docker/Python with persistent disk is required. Sites is available but accepts Cloudflare-compatible JS workers/static sites, not this Python ASGI backend; do not claim a static-only deployment is the full app.

## What works and what is verified

- Python FastAPI + Pydantic + SQLAlchemy/SQLite/FTS5, durable leased jobs, page checkpoints, PDF upload/dedup, typed facts, exact quotes/offsets/word boxes, semantic verification and quarantine.
- React/TypeScript interface: collections, upload, search, results, relationships, source viewer, job coverage, failures, exports.
- Every starter PDF parsed: 511 pages total. A 15-page pilot is disclosed as partial extraction coverage.
- Archived real gpt-oss pilot exports: `samples/actual-runs/*.json.gz`, 52 accepted and 114 quarantined claims after safety audit. They retain original model-run lineage; the Delhivery export now includes two deterministic comparisons recomputed from those claims (one scope reconciliation and one insufficient-context result). These are not GLM outputs or a gold dataset.
- `scripts.import_samples` restores actual exports into a NEW data directory, requiring all source hashes to match the supplied archive. Both real exports were restored successfully, retaining all original PDFs and evidence.
- Saved mode labels itself and disables uploads/resume in UI and API.
- Browser checked saved search, claim detail, and corporate address highlight on annual PDF page 51. The highlight aligned with the actual row. Added cross-page context links, source-page navigation, zoom, modal focus trap/restore, and unrotated evidence/render coordinates.
- 51 tests pass, covering comparison arithmetic/negation/context, provenance, rotated PDFs, upload/dedup, admission limits, lease recovery, unavailable model, saved restoration, reprocess, request budgets, request shape, explicit qualifier retention, ranges, modality/polarity, suppression of noisy same-document dated-series pairs, and safe startup failure when a port is already occupied. Ruff and frontend build are included in `make test`.
- Dockerfile/Compose and deployment instructions exist. A Docker build completed successfully on September 8, 2026 after the earlier registry metadata failures. Rebuild after any subsequent source changes before treating the image as current, then smoke-test the container.

## Runtime and data

- Live-data API: port 8017, exec session 23988, PID 63007 at last start. It has earlier imports; restart to load later Python changes.
- Saved-results API: port 8018, session 75207. `FACT_DATA_DIR=data/qa-saved`, `FACT_SAMPLE_MODE=true`. It serves genuine restored exports, including two deterministic relationship results, and was used for visual QA.
- Worker is STOPPED for handoff. Active incomplete jobs were marked partial with `operator_checkpoint` failure records and leases cleared; queued jobs remain queued. Start only after reviewing provider status/budgets. No background extraction should be assumed active.
- Current primary DB: `data/knowledge.sqlite`; six current accepted claims remain from the limited prospectus reprocess and 166 older claims are superseded. This is not a completed corpus run; preserved exports provide the only broader usable results.
- Original sources are in ignored `starter-datasets.zip`, `data/pdfs/`, and original assignment PDF. `data/pilot-v1.sqlite` preserves early failures. Do not overwrite backups or fabricate accepted claims.
- Pipeline version: `layout-5.claims-5.verify-3.compare-2`. The version was bumped for provider request shape and expanded grounded context/value handling.
- `uv` 0.12.5; `.venv` Python 3.13.15. Node/npm are installed. `gh` authenticates as UtkarsHMer05 with repository scopes. GitHub remote: https://github.com/UtkarsHMer05/factlayer-superjoin (public; README explicitly labels the prototype incomplete). No video or form submission.
- Another unrelated service had occupied port 8000. Do not kill it.

## Next steps, in order

1. Run `make test`, `uv run python -m scripts.status`, and inspect git status. Keep `.env` private. The bounded JSON smoke request currently returns HTTP 429 quickly; wait for quota reset before retrying it, then validate one actual source region with `model.extract`. Record status, elapsed time, usage and failure type without logging credentials or hidden model reasoning.
2. Fix latency/JSON issues while retaining the exact requested model. Requests currently send the whole extraction JSON schema plus active text and first-three-page identity hints; the verifier receives redundant references. Trim redundant context thoughtfully, preserving source IDs and enough issuer/date evidence. Consider smaller source chunks and extraction output batches. Do not disable grounding to get counts up.
3. Rerun selected pilot pages explicitly with `scripts.reprocess --pilot`, then worker. Resuming current partial jobs removes page selection and processes remaining pages, so reprocess is the appropriate fresh pilot command. This preserves superseded claims and model runs. Check accepted source subject, table column, units, scope and date manually against PDFs.
4. Required candidate cases, already located in source PDFs:
   - Corroboration: annual PDF22 and earnings PDF8 report 18,793 PIN codes. Annual as-of March 31, 2024 vs presentation Q4 FY24 needs evidence-supported endpoint normalization. Infographic number gating may currently quarantine the presentation; never bypass it just for the demo.
   - Likely contradiction: SAME annual report PDF31 (printed61) postal122002 vs PDF51 (printed100) postal122001, same corporate office. Earlier prospectus PDF30 postal122002 is extra historical evidence, not enough alone to establish same-date conflict. Source does not establish which code is correct.
   - Context: annual PDF22 standalone revenue74,540.82 million vs consolidated81,415.38 million; earnings PDF17 consolidated8,142 crore is rounded. Alternative: Survey PDF14 GDP6.4 FY25 first advance vs RBI PDF8 GDP6.5 second advance, with release/vintage evidence. Do not assert causal explanations without evidence.
   - Genuine failure: earnings PDF9 flattened chart confused PTL revenue1,517 crore with tonnage1,429 thousand tonnes. Saved original failure in `samples/evaluation/pilot-v1-failures.json`. Demonstrate current quarantine/coverage honestly.
5. Finish and evaluate relationship workflow. Worker now runs deterministic comparisons and calls alignment/reconciliation when the collection queue settles; standalone `scripts.reconcile` remains available. Equivalent predicates are learned from observed labels. Entity aliases are not yet resolved. Context normalization and missing time prevent many legitimate pairs; fix generically using exact evidence. Model semantic judgments need strict numerical/qualification review; missing context must not be upgraded without evidence. Add meaningful regression tests for failures actually found.
6. Broaden to both complete collections only after pilot quality improves and budget is feasible. Report parsing and semantic coverage separately. Never claim all511 pages semantically extracted based on parsing counts. Export refreshed real outputs and evaluate successes plus failures, not just counts.
7. Finish mobile/keyboard/live-upload QA, including interrupted jobs and errors. Desktop saved evidence was verified; a complete mobile pass was not. Record a genuine <=180-second demo with real upload and all four cases. Time skips are allowed if labeled. Do not substitute a scripted animation for successful processing.
8. Rebuild Docker after later source changes, then test container health, upload, worker progress, and volume survival across restart. Use DEPLOYMENT.md. Obtain the already-requested hosting destination if not provided; prepare everything else before asking for account access. Keep provider key in host secrets. This is currently a shared workspace; add practical admission/rate limits and host access control for public judges, or explicitly constrain access to public docs.
9. Secret-scan current files AND git history. Push subsequent verified changes to the existing GitHub repository using the authenticated account. Publish only code/public sample excerpts, not .env/data/archive. Update README with actual repository/deployment/video links only after verifying them. No final hiring-form submission has been authorized.
10. End with exact completed artifacts, checks and remaining dependencies. The previous agent stopped near Codex quota as requested, not because the assignment was finished.

## Important implementation caveats

- Grounding checks quote membership, optional scope must literally occur in context evidence, and quarter headers cannot be reduced to annual periods. It rejects numeric claims from visually ambiguous infographic units. No OCR/vision or cell-grid reconstruction exists.
- The independent verification pass uses the same model and can repeat mistakes. Never equate accepted spans with independently true facts.
- `model.job_context` reserves every HTTP attempt in the job BEFORE network work and counts reported usage, including retries/repairs. Standalone reconciliation has no job context budget. Token limits are thresholds between calls; unknown failed-request usage is not recoverable.
- Current alignment batches120 observed predicates, retrieval limits30 candidates, judgment batches10. Cross-batch aliases and long-corpus coverage need review. Model-proposed alignment is not automatically trusted truth.
- Same-context numeric comparisons use Decimal and source display precision, including bps conversion. Different known context gets a bounded comparability explanation; unknown context abstains. Negative assertion of one value does not contradict a different positive value.
- Old exports have earlier model provenance at run level; newly persisted claims also store model/version. Preserve lineage when refreshing samples.
