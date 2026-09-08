"""Lightweight Vercel entrypoint for the frontend/API shell."""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

app = FastAPI(title='FactLayer', version='0.1.0')


@app.middleware('http')
async def normalize_vercel_path(request: Request, call_next):
    """Normalize paths when Vercel rewrites requests to /api/index.py."""
    # 1. Check explicit __path query parameter passed by Vercel rewrite
    path_override = request.query_params.get('__path')
    if path_override:
        clean = path_override if path_override.startswith('/') else '/' + path_override
        request.scope['path'] = clean
    else:
        # 2. Check Vercel routing headers
        current_path = request.scope.get('path', '')
        if current_path in ('/api/index.py', '/api/index', '/api'):
            matched = (
                request.headers.get('x-vercel-matched-path')
                or request.headers.get('x-matched-path')
                or request.headers.get('x-forwarded-url')
            )
            if matched and matched not in ('/api/index.py', '/api/index'):
                clean_path = matched.split('?')[0]
                request.scope['path'] = clean_path

    return await call_next(request)


# -----------------------------------------------------------------------------
# Demonstration Sample Data
# -----------------------------------------------------------------------------
SAMPLE_COLLECTION = {
    'id': 'col-sample-demo',
    'name': 'Sample Financial Evidence Collection',
    'created': 1725800000,
    'documents': 1,
    'facts': 3,
    'relationships': 1,
}

SAMPLE_DOCUMENT = {
    'id': 'doc-demo-1',
    'collection_id': 'col-sample-demo',
    'filename': 'demo-financial-report.pdf',
    'page_count': 12,
    'parsed_pages': 12,
    'extracted_pages': 12,
    'facts': 3,
    'status': 'completed',
    'job_id': 'job-demo-1',
}

SAMPLE_FACTS = [
    {
        'id': 'fact-1',
        'collection_id': 'col-sample-demo',
        'document_id': 'doc-demo-1',
        'page': 3,
        'status': 'accepted',
        'data': {
            'subject': 'Consolidated Revenue',
            'predicate': 'FY2025 Total Revenue',
            'assertion': 'Consolidated revenue reached $4.2B for fiscal year 2025.',
            'value': {'raw': '$4.2B', 'unit': 'USD', 'scale': 'billion'},
            'context': {'period': 'FY2025', 'currency': 'USD', 'accounting_standard': 'GAAP'},
            'anchors': [
                {
                    'quote': 'Total consolidated revenue was $4.2 billion for the fiscal year ended December 31, 2025.',
                    'page': 3,
                    'boxes': [[50, 120, 480, 140]],
                }
            ],
            'grounding_limit': 'Verified against primary table in Section 4.',
        },
    },
    {
        'id': 'fact-2',
        'collection_id': 'col-sample-demo',
        'document_id': 'doc-demo-1',
        'page': 5,
        'status': 'accepted',
        'data': {
            'subject': 'Operating Margin',
            'predicate': 'Operating Margin Percentage',
            'assertion': 'Operating margin expanded by 240 basis points to 18.4%.',
            'value': {'raw': '18.4%', 'unit': '%', 'scale': 'percentage'},
            'context': {'period': 'FY2025', 'metric_type': 'Non-GAAP'},
            'anchors': [
                {
                    'quote': 'Operating margin expanded to 18.4% compared to 16.0% in the prior year.',
                    'page': 5,
                    'boxes': [[60, 200, 520, 220]],
                }
            ],
            'grounding_limit': 'Cross-referenced with financial statement reconciliation.',
        },
    },
    {
        'id': 'fact-3',
        'collection_id': 'col-sample-demo',
        'document_id': 'doc-demo-1',
        'page': 7,
        'status': 'quarantined',
        'data': {
            'subject': 'Projected AI Investment',
            'predicate': 'CapEx Allocation',
            'assertion': 'Projected capital expenditure of $850M for AI infrastructure in FY2026.',
            'value': {'raw': '$850M', 'unit': 'USD', 'scale': 'million'},
            'context': {'period': 'FY2026 (Forward Looking)'},
            'anchors': [
                {
                    'quote': 'Management expects capital expenditures between $800M and $900M for data center infrastructure.',
                    'page': 7,
                    'boxes': [[55, 310, 490, 330]],
                }
            ],
            'rejection': 'Forward-looking guidance without audit validation.',
            'grounding_limit': 'Quarantined due to predictive assertion phrasing.',
        },
    },
]

SAMPLE_RELATIONSHIPS = [
    {
        'id': 'rel-1',
        'collection_id': 'col-sample-demo',
        'label': 'corroborates',
        'left': {
            'id': 'fact-1',
            'document_id': 'doc-demo-1',
            'page': 3,
            'data': {
                'subject': 'Consolidated Revenue',
                'predicate': 'FY2025 Total Revenue',
                'assertion': 'Consolidated revenue reached $4.2B for fiscal year 2025.',
                'value': {'raw': '$4.2B', 'unit': 'USD', 'scale': 'billion'},
                'anchors': [{'quote': 'Total consolidated revenue was $4.2 billion.', 'page': 3}],
            },
        },
        'right': {
            'id': 'fact-1b',
            'document_id': 'doc-demo-1',
            'page': 11,
            'data': {
                'subject': 'Consolidated Revenue',
                'predicate': 'Audited Segment Revenue Sum',
                'assertion': 'Sum of reported segment revenues equals $4,200 million.',
                'value': {'raw': '$4,200M', 'unit': 'USD', 'scale': 'million'},
                'anchors': [{'quote': 'Enterprise ($2.5B) and Consumer ($1.7B) aggregate to $4,200M.', 'page': 11}],
            },
        },
        'data': {
            'explanation': 'Reported segment revenue aggregation directly corroborates total consolidated revenue.',
            'calculation': {'segment_sum': '$4,200M', 'total_revenue': '$4.2B', 'variance': '0%'},
        },
    }
]

SAMPLE_FAILURES = [
    {
        'id': 'fail-1',
        'collection_id': 'col-sample-demo',
        'filename': 'demo-financial-report.pdf',
        'page': 7,
        'stage': 'grounding',
        'message': 'Assertion quarantined: Forward-looking forecast detected',
        'data': {
            'assertion': 'Projected capital expenditure of $850M for AI infrastructure in FY2026.',
            'handling': 'Separated into quarantined claims to keep unverified guidance visible without contaminating grounded facts.',
        },
    }
]


# -----------------------------------------------------------------------------
# Health Check
# -----------------------------------------------------------------------------
@app.get('/health')
@app.get('/api/health')
@app.get('/api/index.py')
def health():
    return {
        'status': 'ok',
        'model': 'sample-pipeline',
        'pipeline_version': '0.1.0',
        'mode': 'sample',
        'read_only': True,
        'notice': 'The Vercel deployment is a lightweight read-only demonstration shell. Deploy with Docker for local PDF processing and durable worker execution.',
    }


# -----------------------------------------------------------------------------
# Collections API
# -----------------------------------------------------------------------------
@app.get('/collections')
@app.get('/api/collections')
def collections():
    return [SAMPLE_COLLECTION]


@app.post('/collections')
@app.post('/api/collections')
def create_collection():
    return JSONResponse(
        status_code=403,
        content={'detail': 'Read-only demo: Collection creation is disabled on Vercel. Deploy with Docker for persistent storage.'},
    )


# -----------------------------------------------------------------------------
# Documents API
# -----------------------------------------------------------------------------
@app.get('/collections/{cid}/documents')
@app.get('/api/collections/{cid}/documents')
def get_documents(cid: str):
    return [SAMPLE_DOCUMENT]


@app.post('/collections/{cid}/documents')
@app.post('/api/collections/{cid}/documents')
def upload_document(cid: str):
    return JSONResponse(
        status_code=403,
        content={'detail': 'Read-only demo: File uploads and PDF parsing require the Docker worker container.'},
    )


# -----------------------------------------------------------------------------
# Facts API
# -----------------------------------------------------------------------------
@app.get('/collections/{cid}/facts')
@app.get('/api/collections/{cid}/facts')
def get_facts(cid: str, q: str = '', status: str = 'accepted', offset: int = 0):
    filtered = [f for f in SAMPLE_FACTS if not status or f['status'] == status]
    if q.strip():
        query = q.strip().lower()
        filtered = [
            f
            for f in filtered
            if query in f['data']['assertion'].lower()
            or query in f['data']['subject'].lower()
            or query in f['data']['predicate'].lower()
        ]
    return {'items': filtered[offset : offset + 50], 'total': len(filtered)}


@app.get('/facts/{fact_id}')
@app.get('/api/facts/{fact_id}')
def get_fact(fact_id: str):
    for f in SAMPLE_FACTS:
        if f['id'] == fact_id:
            return f
    return SAMPLE_FACTS[0]


# -----------------------------------------------------------------------------
# Relationships API
# -----------------------------------------------------------------------------
@app.get('/collections/{cid}/relationships')
@app.get('/api/collections/{cid}/relationships')
def get_relationships(cid: str, label: str = '', offset: int = 0):
    filtered = [r for r in SAMPLE_RELATIONSHIPS if not label or r['label'] == label]
    return {'items': filtered[offset : offset + 50], 'total': len(filtered)}


@app.get('/relationships/{rel_id}')
@app.get('/api/relationships/{rel_id}')
def get_relationship(rel_id: str):
    for r in SAMPLE_RELATIONSHIPS:
        if r['id'] == rel_id:
            return r
    return SAMPLE_RELATIONSHIPS[0]


# -----------------------------------------------------------------------------
# Failures API
# -----------------------------------------------------------------------------
@app.get('/collections/{cid}/failures')
@app.get('/api/collections/{cid}/failures')
def get_failures(cid: str):
    return SAMPLE_FAILURES


# -----------------------------------------------------------------------------
# Jobs & Source Viewing API
# -----------------------------------------------------------------------------
@app.get('/jobs/{job_id}')
@app.get('/api/jobs/{job_id}')
def get_job(job_id: str):
    return {'id': job_id, 'status': 'completed', 'message': 'Sample demonstration data indexed.'}


@app.get('/documents/{doc_id}/pages/{page}')
@app.get('/api/documents/{doc_id}/pages/{page}')
def get_document_page(doc_id: str, page: int):
    return {
        'docId': doc_id,
        'page': page,
        'width': 612,
        'height': 792,
        'anchors': [
            {'quote': 'Sample extracted evidence snippet.', 'page': page, 'boxes': [[50, 100, 450, 130]]}
        ],
    }


# 1x1 transparent PNG fallback for page preview in read-only demo
SVG_FALLBACK = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="612" height="792" viewBox="0 0 612 792">'
    '<rect width="612" height="792" fill="#fafafa"/>'
    '<text x="50%" y="45%" text-anchor="middle" font-family="sans-serif" font-size="20" fill="#666">'
    'Original Evidence Document (Read-only Demo)'
    '</text>'
    '<text x="50%" y="52%" text-anchor="middle" font-family="sans-serif" font-size="14" fill="#999">'
    'Deploy with Docker for full PDF rendering &amp; OCR processing.'
    '</text>'
    '</svg>'
)


@app.get('/documents/{doc_id}/pages/{page}/image')
@app.get('/api/documents/{doc_id}/pages/{page}/image')
def get_document_page_image(doc_id: str, page: int):
    return Response(content=SVG_FALLBACK, media_type='image/svg+xml')


# -----------------------------------------------------------------------------
# Static Frontend Serving (Fallback if CDN routes to function)
# -----------------------------------------------------------------------------
def _resolve_static_root() -> Path | None:
    candidates = [
        Path(__file__).resolve().parent.parent / 'public',
        Path(__file__).resolve().parent / 'public',
        Path('/var/task/public'),
        Path(__file__).resolve().parent.parent / 'frontend' / 'dist',
    ]
    for c in candidates:
        if (c / 'index.html').is_file():
            return c
    return None


_static_dir = _resolve_static_root()
if _static_dir and (_static_dir / 'assets').is_dir():
    app.mount('/assets', StaticFiles(directory=str(_static_dir / 'assets')), name='assets')


@app.get('/')
@app.get('/index.html')
def frontend():
    if _static_dir and (_static_dir / 'index.html').is_file():
        return FileResponse(_static_dir / 'index.html')
    return Response(content='<!doctype html><html><body><div id="root">Loading FactLayer...</div></body></html>', media_type='text/html')


# -----------------------------------------------------------------------------
# Catch-all API Fallback
# -----------------------------------------------------------------------------
@app.api_route('/{path:path}', methods=['GET', 'POST', 'PUT', 'DELETE'])
def catch_all(path: str):
    if _static_dir and (_static_dir / 'index.html').is_file() and not path.startswith('api'):
        return FileResponse(_static_dir / 'index.html')
    return []
