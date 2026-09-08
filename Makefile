.PHONY: setup build dev test ingest demo export-samples
setup:
	uv sync --locked --extra live
	npm ci --prefix frontend
	npm run build --prefix frontend
build:
	npm run build --prefix frontend
dev:
	uv run python -m scripts.dev
test:
	uv run pytest -q
	uv run ruff check backend scripts tests
	npm run build --prefix frontend
ingest:
	uv run python -m scripts.ingest_starters
demo: dev
export-samples:
	uv run python -m scripts.export_samples
