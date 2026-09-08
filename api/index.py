"""Lightweight Vercel entrypoint for the frontend/API shell."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title='FactLayer')


@app.get('/health')
@app.get('/api/health')
def health():
    return {
        'status': 'ok',
        'mode': 'sample',
        'read_only': True,
        'notice': 'The Vercel shell does not bundle saved evidence or PDF processing. Use Docker for the full application.',
    }


@app.get('/collections')
@app.get('/api/collections')
def collections():
    return []


static_root = Path(__file__).resolve().parents[1] / 'public'
if static_root.exists():
    app.mount('/assets', StaticFiles(directory=static_root / 'assets'), name='assets')

    @app.get('/')
    @app.get('/{path:path}')
    def frontend(path: str = ''):
        return FileResponse(static_root / 'index.html')
