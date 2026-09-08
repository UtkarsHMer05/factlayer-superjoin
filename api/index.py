"""Read-only FactLayer demo entrypoint for Vercel's Python runtime."""

import importlib
import os

# Vercel Functions have no durable filesystem or independent worker process.
# This deployment therefore exposes the reviewed saved-results experience only.
if os.getenv('VERCEL'):
    os.environ.setdefault('FACT_DATA_DIR', 'data/live-work')
    os.environ.setdefault('FACT_SAMPLE_MODE', 'true')
    os.environ.setdefault('FACT_READ_ONLY', 'true')

app = importlib.import_module('backend.factlayer.api').app
