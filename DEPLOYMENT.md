# Deployment

The application requires a Python server and writable persistent storage. Static hosting alone cannot run PDF parsing or the durable worker.

## Container

```sh
cp .env.example .env
# Set FACT_API_KEY in .env using your server-side provider key.
docker compose up --build -d
```

Open http://localhost:8017. Compose mounts a persistent named volume at `/data`. The image runs as UID 10001; host-mounted disks must be writable by this user. The container launches one API and one worker, and exits if either fails. Do not run multiple replicas against separate SQLite files. Back up the whole data directory with the service stopped, or use SQLite's backup API plus a copy of PDFs.

The Dockerfile builds the frontend, installs locked Python dependencies, and serves the frontend through FastAPI. It never copies `.env`, local data, or source archives. `HOST`, `PORT`, and `FACT_DATA_DIR` are configurable. Configure an accessible OpenAI-compatible model URL, model ID, and `FACT_API_KEY` through the host's secret manager. Never use `VITE_` for credentials. Keep the default server-side shared-workspace admission limits (`FACT_UPLOAD_RATE_LIMIT=5`, `FACT_RESUME_RATE_LIMIT=6`, `FACT_RATE_LIMIT_WINDOW_SECONDS=60`) unless the host already supplies an equivalent authenticated gateway.

An up-to-date Docker image built successfully on September 8, 2026, and an isolated saved-mode container returned `200` from `/api/health`. This verifies the image build and basic runtime health; it does not validate live provider extraction, persistent-volume survival, or a public deployment. Native setup, tests, frontend build, and local API/browser execution also work.

## Hosted service checklist

1. Use an existing authenticated Docker/Python hosting account and create one service from this repository. No paid service has been provisioned.
2. Attach persistent storage at `/data`, writable by UID 10001. Set the environment above; use the platform-assigned PORT.
3. Build using the Dockerfile. Set the health endpoint to `/api/health`.
4. Upload a small real PDF, follow its job, and inspect the evidence and a completed relationship. A healthy API does not prove provider access.
5. Restart the service and confirm the same collection and source PDF survive.
6. Open the public URL from a separate session and repeat the judge workflow before sharing it as ready.

This prototype has a shared workspace: all visitors can see collections and uploaded PDFs. It has no user authentication or tenant isolation. Use public demonstration documents only. Per-job request/token caps limit each job, and the API has a lightweight per-client upload/resume admission limit. Add host access control, an authenticated gateway, and durable distributed limits before opening unrestricted uploads to the internet.

No public deployment URL exists yet. An authenticated hosting destination is still needed. The validated local workspace used Xkiro-hosted DeepSeek for a focused source-evidence run; a new hosted provider should be checked with a small upload before public sharing.

## Vercel public demo

This repository is configured for a lightweight **read-only shell** on Vercel. It does not publish PDFs or saved evidence, which keeps the Python function under Vercel's function-size limit. It is useful for verifying the frontend and `/api/health`, but it does not show the reviewed workspace.

It deliberately does **not** accept uploads or run the worker. Vercel Functions do not have durable local storage or a continuously running worker, so treating this demo as a writable ingestion service would lose PDFs and background-job state. The live Docker deployment above remains the supported path for real uploads and processing.

Before importing the repository into Vercel:

1. Do not add `.env` or any API key to Git or Vercel for this shell.
2. Import the GitHub repository in Vercel with its root set to this project and click **Deploy**.
3. Verify `https://YOUR-DEPLOYMENT/api/health` and open the UI.

The Vercel Python function uses the small `requirements.txt` runtime set, while local and Docker live processing enables the `live` dependency extra. The Vite build is emitted to `public/` for CDN delivery. Vercel's FastAPI documentation describes the single-function runtime; its guidance also notes that asynchronous work needs a queue or similar system, and its file guidance recommends object storage for writes. See [FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi), [Python runtime bundling](https://vercel.com/docs/functions/runtimes/python), and [Vercel file guidance](https://vercel.com/kb/guide/how-can-i-use-files-in-serverless-functions).
