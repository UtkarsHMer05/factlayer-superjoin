"""Lightweight Vercel entrypoint for the frontend/API shell."""

from fastapi import FastAPI

app = FastAPI(title='FactLayer')


@app.get('/api/health')
def health():
    return {
        'status': 'ok',
        'mode': 'sample',
        'read_only': True,
        'notice': 'The Vercel shell does not bundle saved evidence or PDF processing. Use Docker for the full application.',
    }


@app.get('/api/collections')
def collections():
    return []


@app.api_route('/api/{path:path}', methods=['GET', 'POST'])
def empty_demo_api(path: str):
    """Keep the shell navigable without packaging the live backend."""
    return []
