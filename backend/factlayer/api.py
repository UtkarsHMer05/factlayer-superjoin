import json
import time
from contextlib import asynccontextmanager
from pathlib import Path

import pymupdf
from fastapi import FastAPI, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import db
from .config import PIPELINE_VERSION, settings
from .ingest import ingest
from .limits import limiter


@asynccontextmanager
async def lifespan(app):
    db.init()
    yield


app = FastAPI(title='FactLayer', version='0.1.0', lifespan=lifespan)


def required(sql, args):
    row = db.one(sql, args)
    if row is None:
        raise HTTPException(404, 'Resource not found')
    return row


def document_file(doc):
    """Resolve a document stored locally or bundled with the read-only demo."""
    recorded = Path(doc['path'])
    if recorded.is_file():
        return recorded
    bundled = settings.data_dir / 'pdfs' / recorded.name
    if bundled.is_file():
        return bundled
    raise HTTPException(404, 'Original PDF is not available')


def guard_expensive_action(request: Request, scope: str, limit: int):
    client = request.client.host if request.client else 'unknown-client'
    if not limiter.allowed(scope, client, limit, settings.rate_limit_window_seconds):
        raise HTTPException(429, f'Too many {scope} requests. Wait a minute and try again.')


class CollectionInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)


@app.get('/api/health')
def health():
    return {'status': 'ok', 'model': settings.model, 'pipeline_version': PIPELINE_VERSION,
            'mode': 'sample' if settings.sample_mode else 'live', 'read_only': settings.read_only,
            'notice': 'Saved results are inspectable without model access. New extraction uses the configured server-side provider.'}


def guard_writable():
    if settings.read_only:
        raise HTTPException(403, 'Read-only public demo: uploads and collection changes are disabled.')


@app.post('/api/collections', status_code=201)
def create_collection(body: CollectionInput):
    guard_writable()
    if not body.name.strip():
        raise HTTPException(422, 'Collection name cannot be blank')
    cid = db.uid()
    db.execute('INSERT INTO collections VALUES(?,?,?)', (cid, body.name.strip(), time.time()))
    return {'id': cid, 'name': body.name.strip()}


@app.get('/api/collections')
def collections():
    return db.rows('''SELECT c.*,
       (SELECT count(*) FROM documents WHERE collection_id=c.id) AS documents,
       (SELECT count(*) FROM claims WHERE collection_id=c.id AND status='accepted') AS facts,
       (SELECT count(*) FROM relationships WHERE collection_id=c.id) AS relationships
       FROM collections c ORDER BY created''')


@app.post('/api/collections/{cid}/documents', status_code=202)
async def upload(cid: str, request: Request, file: UploadFile):
    guard_writable()
    if settings.sample_mode:
        raise HTTPException(403, 'Saved-results mode: uploads are disabled')
    guard_expensive_action(request, 'upload', settings.upload_rate_limit)
    chunks, total = [], 0
    while chunk := await file.read(1024 * 1024):
        total += len(chunk)
        if total > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(413, 'PDF exceeds upload limit')
        chunks.append(chunk)
    try:
        return ingest(cid, file.filename or 'uploaded.pdf', b''.join(chunks))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.get('/api/collections/{cid}/documents')
def documents(cid: str):
    return [db.unpack(r) for r in db.rows('''SELECT d.*,
      (SELECT count(*) FROM pages p WHERE p.document_id=d.id) AS parsed_pages,
      (SELECT count(*) FROM pages p WHERE p.document_id=d.id AND p.status='extracted') AS extracted_pages,
      (SELECT count(*) FROM claims c WHERE c.document_id=d.id AND c.status='accepted') AS facts,
      (SELECT id FROM jobs j WHERE j.document_id=d.id ORDER BY created DESC LIMIT 1) AS job_id
      FROM documents d WHERE collection_id=? ORDER BY created''', (cid,))]


@app.get('/api/jobs/{jid}')
def job(jid: str):
    return db.unpack(required('SELECT * FROM jobs WHERE id=?', (jid,)))


@app.post('/api/jobs/{jid}/resume')
def resume(jid: str, request: Request):
    guard_writable()
    if settings.sample_mode:
        raise HTTPException(403, 'Saved-results mode: processing is disabled')
    guard_expensive_action(request, 'resume', settings.resume_rate_limit)
    old = required('SELECT * FROM jobs WHERE id=?', (jid,))
    if old['status'] not in ('partial', 'failed'):
        raise HTTPException(409, 'Only partial or failed jobs can resume')
    db.execute("UPDATE jobs SET status='queued',options='{}',requests=0,tokens=0,lease=0,message='Resuming remaining pages',updated=? WHERE id=?", (time.time(), jid))
    return {'id': jid, 'status': 'queued'}


@app.get('/api/collections/{cid}/facts')
def facts(cid: str, q: str = '', document: str = '', status: str = 'accepted',
          limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    clauses, args = ['collection_id=?', 'status=?'], [cid, status]
    if q:
        clauses.append('(subject LIKE ? OR predicate LIKE ? OR data LIKE ?)')
        args.extend(['%' + q + '%'] * 3)
    if document:
        clauses.append('document_id=?')
        args.append(document)
    where = ' AND '.join(clauses)
    total = db.one('SELECT count(*) AS n FROM claims WHERE ' + where, args)['n']
    return {'total': total, 'items': [db.unpack(r) for r in db.rows('SELECT * FROM claims WHERE ' + where + ' ORDER BY rowid LIMIT ? OFFSET ?', [*args, limit, offset])]}


@app.get('/api/facts/{fid}')
def fact(fid: str):
    row = db.unpack(required('SELECT * FROM claims WHERE id=?', (fid,)))
    row['document'] = db.unpack(required('SELECT * FROM documents WHERE id=?', (row['document_id'],)))
    row['relationships'] = [db.unpack(r) for r in db.rows('SELECT * FROM relationships WHERE left_id=? OR right_id=?', (fid, fid))]
    return row


@app.get('/api/collections/{cid}/relationships')
def relationships(cid: str, label: str = '', limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    where, args = 'collection_id=?', [cid]
    if label:
        where += ' AND label=?'
        args.append(label)
    total = db.one('SELECT count(*) AS n FROM relationships WHERE ' + where, args)['n']
    result = []
    for r in db.rows('SELECT * FROM relationships WHERE ' + where + ' ORDER BY rowid LIMIT ? OFFSET ?', [*args, limit, offset]):
        r = db.unpack(r)
        r['left'] = db.unpack(db.one('SELECT * FROM claims WHERE id=?', (r['left_id'],)))
        r['right'] = db.unpack(db.one('SELECT * FROM claims WHERE id=?', (r['right_id'],)))
        result.append(r)
    return {'total': total, 'items': result}


@app.get('/api/relationships/{rid}')
def relationship(rid: str):
    row = db.unpack(required('SELECT * FROM relationships WHERE id=?', (rid,)))
    row['left'], row['right'] = fact(row['left_id']), fact(row['right_id'])
    return row


@app.get('/api/documents/{did}/pages/{number}')
def page_data(did: str, number: int):
    return db.unpack(required('SELECT * FROM pages WHERE document_id=? AND number=?', (did, number)))


@app.get('/api/documents/{did}/pages/{number}/image')
def page_image(did: str, number: int, width: int = Query(1600, ge=300, le=2400)):
    doc = required('SELECT * FROM documents WHERE id=?', (did,))
    if number < 1 or number > doc['page_count']:
        raise HTTPException(404, 'Page not found')
    with pymupdf.open(document_file(doc)) as pdf:
        page = pdf[number - 1]
        page.set_rotation(0)  # Evidence coordinates use the unrotated PDF space.
        image = page.get_pixmap(matrix=pymupdf.Matrix(width / page.rect.width, width / page.rect.width), alpha=False)
        return Response(image.tobytes('png'), media_type='image/png', headers={'Cache-Control': 'private, max-age=3600'})


@app.get('/api/documents/{did}/source')
def source(did: str):
    doc = required('SELECT * FROM documents WHERE id=?', (did,))
    return FileResponse(document_file(doc), media_type='application/pdf', filename=doc['filename'])


@app.get('/api/collections/{cid}/failures')
def failures(cid: str):
    return [db.unpack(r) for r in db.rows('SELECT f.*,d.filename FROM failures f JOIN documents d ON d.id=f.document_id WHERE d.collection_id=? ORDER BY f.created DESC', (cid,))]


@app.get('/api/collections/{cid}/export')
def export(cid: str):
    collection = required('SELECT * FROM collections WHERE id=?', (cid,))
    result = {'collection': collection, 'pipeline_version': PIPELINE_VERSION, 'model': settings.model,
              'exported_at': time.time(), 'provenance': 'actual_pipeline_output', 'documents': documents(cid)}
    for table in ['claims', 'relationships', 'registry']:
        result[table] = [db.unpack(r) for r in db.rows(f'SELECT * FROM {table} WHERE collection_id=?', (cid,))]
    for table in ['pages', 'evidence', 'failures', 'runs']:
        result[table] = [db.unpack(r) for r in db.rows(f'SELECT t.* FROM {table} t JOIN documents d ON t.document_id=d.id WHERE d.collection_id=?', (cid,))]
    for d in result['documents']:
        d.pop('path', None)
    return Response(json.dumps(result, ensure_ascii=False, indent=2), media_type='application/json',
                    headers={'Content-Disposition': f'attachment; filename="factlayer-{cid[:8]}.json"'})


dist = Path(__file__).resolve().parents[2] / 'frontend' / 'dist'
if dist.exists():
    app.mount('/', StaticFiles(directory=dist, html=True), name='frontend')
