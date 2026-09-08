import hashlib
import time
from pathlib import Path

import pymupdf

from . import db
from .config import PIPELINE_VERSION, settings


def ingest(collection_id, filename, content, options=None):
    if not db.one('SELECT id FROM collections WHERE id=?', (collection_id,)):
        raise ValueError('Collection not found')
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise ValueError(f'PDF exceeds {settings.max_upload_mb} MB upload limit')
    if not content.startswith(b'%PDF-'):
        raise ValueError('File does not have a PDF signature')
    try:
        with pymupdf.open(stream=content, filetype='pdf') as pdf:
            if pdf.needs_pass:
                raise ValueError('Encrypted PDF: provide an unlocked copy')
            pages = len(pdf)
            if pages < 1 or pages > settings.max_pages:
                raise ValueError(f'PDF must contain 1–{settings.max_pages} pages')
    except (pymupdf.FileDataError, RuntimeError) as exc:
        raise ValueError('PDF cannot be parsed') from exc
    digest = hashlib.sha256(content).hexdigest()
    previous = db.one('SELECT * FROM documents WHERE collection_id=? AND hash=?', (collection_id, digest))
    if previous:
        job = db.one('SELECT * FROM jobs WHERE document_id=? ORDER BY created DESC LIMIT 1', (previous['id'],))
        return {'document_id': previous['id'], 'job_id': job['id'] if job else None, 'deduplicated': True}
    doc_id, job_id = db.uid(), db.uid()
    directory = settings.data_dir / 'pdfs'
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (digest + '.pdf')
    if not path.exists():
        path.write_bytes(content)
    now = time.time()
    with db.connect() as c:
        c.execute('INSERT INTO documents(id,collection_id,hash,filename,path,page_count,created,metadata) VALUES(?,?,?,?,?,?,?,?)',
                  (doc_id, collection_id, digest, Path(filename).name, str(path.resolve()), pages, now, db.dumps({'pipeline_version': PIPELINE_VERSION})))
        c.execute('INSERT INTO jobs(id,document_id,status,total,options,created,updated) VALUES(?,?,?,?,?,?,?)',
                  (job_id, doc_id, 'queued', pages, db.dumps(options or {}), now, now))
    return {'document_id': doc_id, 'job_id': job_id, 'deduplicated': False}
