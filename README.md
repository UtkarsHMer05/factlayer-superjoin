# FactLayer — Evidence-First PDF Knowledge Layer

> Superjoin VIT 2026 assignment submission

**Demo video:** [Watch the demo](https://drive.google.com/file/d/1a3ydxa3LQ4f_7QomGshSKRMHHjOpXL1-/view?usp=sharing)

**Repository:** `ADD_YOUR_GITHUB_REPOSITORY_LINK_HERE`

FactLayer turns a collection of PDFs into an inspectable fact layer. It extracts small, source-grounded assertions, compares related assertions across documents, explains important differences, and preserves failures instead of hiding them.

The central design principle is simple: **source first, conclusions second.** Every displayed relationship links back to the supporting PDF page and quoted evidence.

## What It Demonstrates

The included reviewed Delhivery workspace contains two public PDFs and demonstrates all four outcomes required by the assignment.

| Required case | Result shown in FactLayer | Evidence to inspect |
| --- | --- | --- |
| Cross-document corroboration | **Corroborated** | Delhivery reaches **18,793 PIN codes** in the annual report (page 22) and Q4 FY24 earnings presentation (page 8). |
| Likely contradiction | **Likely contradiction** | The corporate-address postal code appears as **122001** on page 51 and **122002** on page 30. The system does not claim that either source is correct. |
| Context-based explanation | **Context explained** | FY24 standalone revenue is **₹74,540.82m**, while consolidated revenue is **₹81,415.38m**. These differ because the reporting scope differs. |
| Failure handling | **Quarantined failure** | On annual-report page 2, chart/infographic numbers are marked for visual verification rather than being accepted as unsupported structured facts. |

The completed workspace currently has **49 grounded facts**, **5 visible relationships**, and an inspectable failure history. The extra relationship records an insufficient-context result, demonstrating that the system can abstain when evidence is not strong enough.

## How It Works

```text
PDF upload
   ↓
PyMuPDF parsing: text, words, bounding boxes, page geometry
   ↓
Model proposes small, typed claims with exact source quotes
   ↓
Deterministic grounding validates quote and value support
   ↓
Cross-document retrieval, predicate alignment, and comparison
   ↓
Facts, relationships, source highlights, and visible failures
```

- **React + TypeScript + Vite** provides the evidence-focused interface.
- **FastAPI** exposes the API and serves the built frontend in local development.
- **SQLite + SQLAlchemy** store documents, page checkpoints, claims, evidence, jobs, relationships, and failures.
- **PyMuPDF** extracts PDF text and page-level source geometry.
- An **OpenAI-compatible model endpoint** proposes and evaluates evidence-backed claims. The reviewed run uses Xkiro with `deepseek/deepseek-v4-flash`; the provider can be changed through environment variables.
- A background worker processes documents durably with leases and resumable page checkpoints.

## Key Product Behaviours

- Upload one or more PDFs into a collection.
- Inspect grounded facts with their exact source quote and page location.
- Compare facts across documents and label the outcome as corroborated, likely contradictory, context explained, or insufficient context.
- Explain scope, time, unit, and reporting-basis differences instead of treating every numeric difference as a contradiction.
- Quarantine unsupported, ambiguous, visual-only, or failed extractions in **Failures & coverage**.
- Preserve partial progress and make provider failures resumable; the app does not silently substitute another model.
- Open the original PDF or a highlighted source page directly from a fact or relationship.

## Quick Start

### Prerequisites

- Python 3.11 or later
- [uv](https://docs.astral.sh/uv/)
- Node.js 20 or later and npm
- An API key for an OpenAI-compatible model provider if you want to process new PDFs

### Install

```sh
git clone YOUR_REPOSITORY_URL
cd "SUPERJOIN ASSINGMENT"
make setup
cp .env.example .env
```

Set `FACT_API_KEY` in `.env`. Do not commit this file or expose the key in client-side code.

The default `.env.example` is configured for the reviewed provider/model pair. To use another OpenAI-compatible provider, update only these variables:

```dotenv
FACT_MODEL=provider/model-id
FACT_MODEL_URL=https://provider.example/v1
FACT_API_KEY=your_server_side_key
```

### Run a new live collection

```sh
make dev
```

Open [http://127.0.0.1:8017](http://127.0.0.1:8017). This starts the API and worker. Upload PDFs from the interface, then use **Documents**, **Facts**, **Relationships**, and **Failures & coverage** to inspect the results.

If port 8017 is already occupied, either open the app already running there or choose another port:

```sh
PORT=8022 uv run python -m scripts.dev
```

### Run the reviewed assignment workspace

The repository includes `data/live-work`, a reviewed local workspace containing the two public source PDFs and the saved evidence needed for the four cases above.

```sh
PORT=8022 FACT_DATA_DIR=data/live-work uv run python -m scripts.dev
```

Then open [http://127.0.0.1:8022](http://127.0.0.1:8022) and select **Relationships**. This is the recommended local setup for recording the demo video.

## Demo Walkthrough

For a three-minute submission video, use the reviewed workspace and show the following in order:

1. Open **Documents** and show the two parsed PDFs.
2. Open **Relationships** and select the **18,793 PIN codes** relationship. Show both source excerpts and their linked pages to demonstrate cross-document corroboration.
3. Select the **corporate address** relationship. Show the two postal codes and explain that the result is a likely contradiction, not an unsupported decision about which source is right.
4. Select the **FY24 revenue** relationship. Explain that standalone and consolidated figures differ because they cover different reporting scopes.
5. Open **Failures & coverage**, select the page-2 visual-layout item, and explain that the candidate numbers were quarantined for human verification rather than silently accepted.
6. Close by returning to a relationship and opening its highlighted source page, reinforcing that every conclusion remains inspectable.

## Verification

Run the full local verification suite with:

```sh
make test
```

This runs the Python tests, Ruff static checks, TypeScript compilation, and the production Vite build. The current project passes **65 automated tests**.

Useful individual commands:

```sh
uv run pytest -q
uv run ruff check backend scripts tests
npm run build --prefix frontend
```

## Deployment

The project includes a Vercel configuration for a **read-only public demonstration** of the reviewed workspace. It bundles the public source PDFs and the saved SQLite evidence database. It is suitable for sharing the completed four-case results, but not for processing fresh uploads in production because serverless functions do not provide durable background-worker storage.

Before deploying:

1. Commit `data/live-work` because it contains the reviewed public PDFs and saved workspace.
2. Confirm the PDFs are safe to make public.
3. Do not add `.env` or any API key to Git or Vercel for the read-only demo.
4. Import the repository in Vercel and deploy. The included `vercel.json` supplies the build, routing, and bundled-data configuration.

For the full deployment notes, see [DEPLOYMENT.md](DEPLOYMENT.md).

For a live, persistent upload workflow, deploy the API and worker together using the Docker deployment described there, with durable storage and server-side model credentials.

## Project Structure

```text
backend/factlayer/       FastAPI application, worker, extraction, grounding, comparison
frontend/                React/TypeScript user interface
api/index.py             Vercel ASGI entry point
data/live-work/          Reviewed public source PDFs and saved local evidence workspace
scripts/                 Local development, ingestion, export, status, and reprocessing tools
tests/                   Automated backend and behaviour tests
vercel.json              Read-only Vercel-demo configuration
DEPLOYMENT.md            Local, Docker, and Vercel deployment instructions
```

## Evidence and Safety Design

FactLayer is deliberately cautious:

- A model response is only a candidate; deterministic grounding checks whether the quoted source text and claimed value are supported.
- Ambiguous layouts, unsupported scope, dropped qualifiers, and visual/chart claims can be quarantined instead of being promoted to facts.
- Numerical comparisons account for decimals, scale, display precision, and explicit scope or time differences.
- When the system lacks enough evidence, it records **insufficient context** instead of manufacturing a conclusion.
- Facts, evidence, model runs, page checkpoints, and failures are retained so the output can be audited and reprocessed.

## Known Limitations

- The included workspace is a focused, reviewed two-document demonstration; it is not a claim that every page has been fully extracted semantically.
- Complex tables, charts, scans, and visual layouts may be omitted or routed to human verification. OCR/vision-based recovery is not yet included.
- A model is used for both claim proposals and semantic interpretation, so model errors remain possible and require evidence review.
- The Vercel deployment is intentionally read-only. Live upload processing needs a durable worker deployment.
- The system is a demonstration project, not a multi-tenant production service: authentication, tenant isolation, and distributed rate controls would be required before broad public use.

## AI Use Disclosure

Codex was used for planning, implementation, debugging, test work, and browser verification. An Xkiro-hosted DeepSeek model was used for the focused source extraction and evidence-judgement workflow. No model was fine-tuned. The original PDF evidence remains visible in the product so that model-generated interpretations can be reviewed.

## Submission Checklist

- [ ] Replace the three placeholder links at the top of this README.
- [ ] Commit the reviewed workspace and all project changes.
- [ ] Push the repository to GitHub.
- [ ] Deploy the read-only demo to Vercel and replace the live-demo link.
- [ ] Record the three-minute demo video and replace the video link.
- [ ] Confirm the GitHub repository, deployed demo, and video links are accessible to reviewers.

---

Built for the Superjoin VIT 2026 assignment.
