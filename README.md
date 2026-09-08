# FactLayer

A local Fact Knowledge Layer prototype for the Superjoin engineering assignment. Upload PDFs, inspect extracted assertions and their original source locations, compare claims, and see failures explicitly.

**Status: functional prototype, not submission-ready.** The API/UI and 29 automated tests work. A real 15-page extraction pilot ran across all six starter PDFs; every document was parsed, but semantic extraction is not yet reliable enough for the four required demonstrations. Read [CONTINUATION.md](CONTINUATION.md) before extending or submitting.

## Setup and Run Instructions

Requires Python 3.11+, `uv`, Node.js 20+, and npm. Versions are resolved in `uv.lock` and `frontend/package-lock.json`.

```sh
make setup
make dev
```

Open [FactLayer](http://127.0.0.1:8017) and [API documentation](http://127.0.0.1:8017/docs). Port 8017 avoids another service already on port 8000 in the development machine. The dev command starts both API and worker. For frontend hot reload, run `npm run dev --prefix frontend` separately.

The user subsequently supplied TokenRouter access. A real smoke request to `https://api.tokenrouter.com/v1/chat/completions` using `z-ai/glm-5.3-free` succeeded. Copy `.env.example` to `.env`, set `FACT_API_KEY` on the server, and use its TokenRouter model/base URL. A nonempty key selects the remote adapter, so Ollama is unnecessary for this configuration. Do not put the key in frontend code or `VITE_` variables. A new extraction pilot on this model remains pending; existing exports used the earlier Ollama model.

For the optional Ollama configuration, clear `FACT_API_KEY`, set `FACT_MODEL=gpt-oss:120b-cloud` and `FACT_MODEL_URL=http://127.0.0.1:11434`, then:

```sh
cp .env.example .env
ollama serve
ollama pull gpt-oss:120b-cloud
```

Use an existing Ollama login (`ollama signin` if required). Cloud availability and limits depend on your account; do not purchase access just to inspect this prototype. `gpt-oss:120b-cloud` was successfully used in this development session. The registered `glm-5:cloud` was retired and `glm-5.1:cloud` required an upgrade, so neither is the default. Ollama cloud does not guarantee constrained JSON; model output is parsed and validated in code. See [Ollama cloud](https://docs.ollama.com/cloud) and [structured outputs](https://docs.ollama.com/capabilities/structured-outputs).

The app always retains parsed evidence if model access fails. Existing local database results remain inspectable without the model. Portable saved-result import is **not implemented yet**; actual JSON exports are included under `samples/actual-runs/` for inspection, with explicit partial status. They are development outputs, not a validated gold dataset.

With the supplied `starter-datasets.zip` in the project root:

```sh
make ingest                  # disclosed 15-page pilot, while parsing all 511 pages
uv run python -m scripts.reconcile  # alias discovery + semantic comparisons; requires model access
make export-samples
make test
```

Run reconciliation only after jobs settle. The worker currently performs deterministic comparison automatically; semantic alias/reconciliation is a separate command and needs integration. `--full` on `scripts.ingest_starters` requests all pages only for newly ingested documents; duplicate uploads reuse existing jobs. Use Resume on partial jobs to process remaining pages. Do not launch a full run until the extraction issues in CONTINUATION.md are resolved.

API example:

```sh
curl -X POST http://127.0.0.1:8017/api/collections \
  -H 'Content-Type: application/json' -d '{"name":"My sources"}'
# Substitute the returned collection id:
curl -X POST http://127.0.0.1:8017/api/collections/COLLECTION_ID/documents \
  -F 'file=@example.pdf'
```

## Video Demo

Not recorded yet. A final video must be no longer than three minutes and demonstrate a real upload plus the four required cases. Do not treat this repository as a finished submission. The planned script is in ANALYSIS_AND_AGENT_HANDOFF.md.

## Approach

FastAPI serves the React/TypeScript interface and API. SQLAlchemy manages SQLite connections; explicit SQL implements the schema and FTS5 retrieval. A separate worker claims persisted jobs under a lease, retains page checkpoints, and stores exact evidence spans and coordinates. Uploaded bytes are deduplicated by SHA-256 within each collection.

PyMuPDF extracts words and blocks. Facing-page detection uses geometry, gutters and footer labels rather than filenames. Claims use a generic typed envelope; predicates are discovered from source content. The model proposes source quotes and context, and code verifies source membership and numeric tokens. An additional model pass checks interpretation, but real pilots show that a second model pass can repeat the first model's error. Therefore ambiguous infographic numbers and unsupported scope/quarter metadata are now rejected in code.

The comparison module uses Decimal arithmetic, unit scaling, explicit context differences and abstention. The separate alignment module discovers predicate aliases from observed assertions and can judge remaining pairs against their evidence. Its live results are not yet evaluated. Original claim text and normalized representations are kept together; claims are never seeded with the expected demonstration values.

AI tools used: Codex for planning, implementation and debugging; Ollama-hosted gpt-oss:120b-cloud for actual extraction/verification. Impeccable guided UI structure; the PDF and Playwright skills guided document inspection and browser checks. No fine-tuning or document-specific runtime rules.

## Limitations and Next Steps

- Extracted table/header associations and subject attribution remain unreliable. Some first-pass source-matching claims were semantically wrong; known failures are preserved in `samples/evaluation/pilot-v1-failures.json`.
- The latest guards quarantine unsupported scope, dropped quarter qualifiers and infographic numbers. A complete new pilot with the improved prompt is still needed.
- Source-spans verified is not equivalent to factually true. The verifier shares the extractor's model and is not an independent truth oracle.
- No OCR/vision fallback, table cell structure, full context inheritance, portable sample import, finished video, or remote repository publication yet.
- Semantic reconciliation is a manual CLI step. Its budget accounting and cache/invalidation need completion.
- The UI needs the final desktop/mobile and keyboard verification pass. Cross-page evidence highlighting needs separation by page.
- Automated tests check behavior with controlled inputs; they do not prove corpus accuracy. No corpus-wide precision/recall claim is made.

## Additional Notes

The source PDFs are public starter files supplied by the user; the archive is ignored by git. Runtime files stay under ignored `data/`. Actual exports contain public source excerpts and model outputs, never credentials. The assignment's full requirements and verified candidate source pages are in ANALYSIS_AND_AGENT_HANDOFF.md.

No GitHub repository, hosted video, or form submission has been created. External publication requires authorization and an authenticated destination.
