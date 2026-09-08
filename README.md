# FactLayer

A PDF Fact Knowledge Layer for the Superjoin assignment: upload documents, inspect extracted assertions at their source locations, and compare evidence with explicit uncertainty.

**Status: working local prototype; not submission-ready.** Native setup, the React build, and 36 automated tests pass. All six starter PDFs (511 pages) have been parsed. Actual saved pilot results contain 52 accepted and 114 quarantined claims. The fresh TokenRouter pilot, the four required demonstration cases, public deployment, and final video remain incomplete. See [CONTINUATION.md](CONTINUATION.md).

## Setup and Run Instructions

Requires Python 3.11+, uv, Node.js 20+, and npm. Dependencies are locked in `uv.lock` and `frontend/package-lock.json`.

```sh
make setup
cp .env.example .env
# Set FACT_API_KEY in .env. Keep it server-side.
make dev
```

Open [FactLayer](http://127.0.0.1:8017) or the [API reference](http://127.0.0.1:8017/docs). The development command starts both API and worker. For frontend hot reload, separately run `npm run dev --prefix frontend`.

The requested provider is `https://api.tokenrouter.com/v1`, model `z-ai/glm-5.3-free`. A nonempty `FACT_API_KEY` selects the OpenAI-compatible adapter. An earlier real smoke request succeeded; later small and full extraction requests were slow or timed out. Low reasoning effort and a bounded output limit are configured. The model's [official API reference](https://docs.z.ai/api-reference/llm/chat-completion) documents GLM-5.3's effort control; actual TokenRouter behavior still needs successful full-run validation. No provider fallback happens silently.

For optional Ollama use, clear `FACT_API_KEY` and set `FACT_MODEL` and `FACT_MODEL_URL` to an accessible Ollama model/base URL. The archived pilot used `gpt-oss:120b-cloud`; it is not represented as a TokenRouter result.

With the supplied `starter-datasets.zip` in the project root:

```sh
make ingest                         # 15 selected extraction pages; all 511 pages parsed
uv run python -m scripts.status      # safe progress/counts, no credentials
uv run python -m scripts.reconcile   # optional explicit semantic comparison rerun
make export-samples
make test
```

Ordinary uploads request all pages. The worker automatically runs deterministic comparison and performs predicate alignment plus semantic reconciliation when a collection's queued jobs settle. Comparison failures are recorded. Semantic accuracy is not yet validated on the required examples.

Resume processes remaining pages. To explicitly replace selected extracted pages after changing the pipeline, stop the worker, wait for its lease to expire, then use `uv run python -m scripts.reprocess --pilot` and restart the worker. Old claims are marked superseded and old model runs retained. Reprocess rejects active leases. `--document ID --pages 22,31` selects pages; omitting page options selects all pages. Cached outputs are keyed by source input, model, and pipeline version; bump the version for prompt/interpretation changes.

### Inspect genuine saved results without a model

Use a fresh data directory and the original source archive. Restoration checks every PDF against the SHA-256 hash in the export; it does not invent or approve claims.

```sh
FACT_DATA_DIR=data/saved FACT_SAMPLE_MODE=true uv run python -m scripts.import_samples samples/actual-runs/*.json.gz
FACT_DATA_DIR=data/saved FACT_SAMPLE_MODE=true uv run python -m scripts.dev
```

The UI labels saved mode, disables upload/resume, and shows original extraction coverage. Exports are development outputs with known limitations, not a gold dataset. All original PDFs remain inspectable. The compressed exports include their actual model runs and evidence. Re-importing into an existing collection is rejected.

Container setup and honest build/deployment status are in [DEPLOYMENT.md](DEPLOYMENT.md).

## Video Demo

Not completed. The final video must be no longer than three minutes and show a real upload plus corroboration, a likely contradiction, contextual reconciliation, and an actual failure. The source candidates and script are in [ANALYSIS_AND_AGENT_HANDOFF.md](ANALYSIS_AND_AGENT_HANDOFF.md). No finished-video or submission link is claimed.

## Approach

FastAPI serves the React/TypeScript UI and API. SQLAlchemy manages SQLite connections; explicit SQL provides durable jobs and FTS5 candidate retrieval. Workers claim jobs under renewable leases and persist page checkpoints. Uploaded bytes are deduplicated by SHA-256 inside collections.

PyMuPDF retains source text, word offsets, boxes, page geometry, and facing-page regions. The model discovers predicates and proposes typed atomic claims with explicit context and exact quotes. Deterministic grounding verifies source membership and value support; a second model pass checks interpretation. Exact source matching is not proof that the interpretation is correct. Unsupported scope, dropped quarter qualifiers, and ambiguous infographic numbers are quarantined.

Comparisons use Decimal arithmetic, scale conversion, display precision, explicit temporal/scope differences, and abstention when context is missing. Predicate aliases are proposed from actual observed labels. Remaining semantic judgments retain source evidence and public explanations. There are no document-specific runtime answers, company rules, or hard-coded demonstration relationships.

Source inspection supports highlighted evidence, separately linked context pages, page navigation, zoom, the original PDF, and keyboard focus handling. API exports retain actual claims, evidence, failures, model runs, and registry entries. Each new claim records its model and pipeline version.

AI tools used: Codex for planning/implementation/debugging; Ollama-hosted gpt-oss for the archived pilot; TokenRouter GLM-5.3 integration and attempted fresh pilot. No fine-tuning. PDF, Impeccable, and Playwright guidance informed document analysis and interface work.

## Limitations and Next Steps

- The four required corpus demonstrations are not yet validated; saved outputs currently have no relationships. Controlled comparison tests do not establish corpus accuracy.
- No OCR/vision or reconstructed table-cell fallback. Charts and complex tables may be quarantined or omitted. The same model performs extraction and semantic verification, so errors may repeat.
- TokenRouter full extraction remains unverified. Requests have timeouts and per-job accounting, including retries/repairs. Token caps are stop thresholds between calls; a final response can exceed the threshold. Unknown usage after network failure cannot be measured locally.
- Semantic alignment has bounded batches and strict observed-label checks, but needs accuracy review and improved cache/budget handling for standalone CLI use.
- Desktop source highlighting and restored sample browsing were checked. A full mobile/accessibility and live-upload acceptance pass remains.
- Docker builds were blocked downloading base images. No host account, public URL, final video, or hiring-form submission has been completed.
- Shared-workspace deployment lacks authentication, tenant isolation, and public admission/rate limits; see deployment notes before unrestricted public use.

## Additional Notes

Original archives/PDFs, credentials, runtime databases, and screenshots are ignored by git. `samples/evaluation/pilot-v1-failures.json` preserves genuine extraction mistakes rather than hiding them. The full assignment analysis remains in [ANALYSIS_AND_AGENT_HANDOFF.md](ANALYSIS_AND_AGENT_HANDOFF.md).
