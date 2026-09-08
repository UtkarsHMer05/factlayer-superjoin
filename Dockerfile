FROM node:22-bookworm-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim-bookworm
RUN pip install --no-cache-dir uv==0.12.5
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --extra live
COPY backend/ backend/
COPY scripts/ scripts/
COPY --from=frontend /app/frontend/dist frontend/dist
ENV HOST=0.0.0.0 PORT=8017 FACT_DATA_DIR=/data PYTHONUNBUFFERED=1
RUN mkdir /data && useradd --uid 10001 --create-home app && chown -R app:app /app /data
USER app
EXPOSE 8017
HEALTHCHECK --interval=30s --timeout=5s CMD ["/app/.venv/bin/python", "-c", "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8017')+'/api/health', timeout=4)"]
CMD ["/app/.venv/bin/python", "-m", "scripts.dev"]
