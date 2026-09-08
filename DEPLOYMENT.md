# Deployment

The application requires a Python server and writable persistent storage. Static hosting alone cannot run PDF parsing or the durable worker.

## Container

```sh
cp .env.example .env
# Set FACT_API_KEY in .env using the supplied server-side TokenRouter key.
docker compose up --build -d
```

Open http://localhost:8017. Compose mounts a persistent named volume at `/data`. The image runs as UID 10001; host-mounted disks must be writable by this user. The container launches one API and one worker, and exits if either fails. Do not run multiple replicas against separate SQLite files. Back up the whole data directory with the service stopped, or use SQLite's backup API plus a copy of PDFs.

The Dockerfile builds the frontend, installs locked Python dependencies, and serves the frontend through FastAPI. It never copies `.env`, local data, or source archives. `HOST`, `PORT`, and `FACT_DATA_DIR` are configurable. Configure `FACT_MODEL=z-ai/glm-5.3-free`, `FACT_MODEL_URL=https://api.tokenrouter.com/v1`, and `FACT_API_KEY` through the host's secret manager. Never use `VITE_` for credentials.

Local Docker builds were attempted twice on September 8, 2026. Both stopped while downloading base-image metadata (`context deadline exceeded`), before application build execution. Container execution is therefore **not verified**. Native setup, tests, frontend build, and local API/browser execution do work.

## Hosted service checklist

1. Use an existing authenticated Docker/Python hosting account and create one service from this repository. No paid service has been provisioned.
2. Attach persistent storage at `/data`, writable by UID 10001. Set the environment above; use the platform-assigned PORT.
3. Build using the Dockerfile. Set the health endpoint to `/api/health`.
4. Upload a small real PDF, follow its job, and inspect the evidence and a completed relationship. A healthy API does not prove provider access.
5. Restart the service and confirm the same collection and source PDF survive.
6. Open the public URL from a separate session and repeat the judge workflow before sharing it as ready.

This prototype has a shared workspace: all visitors can see collections and uploaded PDFs. It has no user authentication or tenant isolation. Use public demonstration documents only. Per-job request/token caps limit each job; there is no global public-user spending/rate limit. Add host access control and admission/rate limits before opening unrestricted uploads to the internet.

No public deployment URL exists yet. An authenticated hosting destination is still needed. The requested TokenRouter model also needs a successful full extraction run; recent requests timed out despite an earlier successful connectivity check.
