"""Explicit, versioned reprocessing; preserve old claims and model runs for audit."""
import argparse
import json
import time

from backend.factlayer import db
from backend.factlayer.config import PIPELINE_VERSION
from scripts.ingest_starters import PILOT


def reprocess(doc_id, pages=None):
    doc = db.one('SELECT * FROM documents WHERE id=?', (doc_id,))
    if not doc:
        raise ValueError('Document not found')
    active = db.one("SELECT id FROM jobs WHERE document_id=? AND status IN ('parsing','extracting','comparing') AND lease>?", (doc_id, time.time()))
    if active:
        raise ValueError('Cannot reprocess a document with an active worker lease')
    selected = pages or list(range(1, doc['page_count'] + 1))
    if any(n < 1 or n > doc['page_count'] for n in selected):
        raise ValueError('Selected page outside document')
    placeholders = ','.join('?' for _ in selected)
    with db.connect() as c:
        ids = [r['id'] for r in c.execute(f'SELECT id FROM claims WHERE document_id=? AND page IN ({placeholders})', [doc_id, *selected])]
        for fid in ids:
            c.execute('DELETE FROM relationships WHERE left_id=? OR right_id=?', (fid, fid))
            c.execute('DELETE FROM claim_search WHERE id=?', (fid,))
            c.execute("UPDATE claims SET status='superseded' WHERE id=?", (fid,))
        c.execute(f"UPDATE pages SET status='parsed' WHERE document_id=? AND number IN ({placeholders})", [doc_id, *selected])
        c.execute("UPDATE jobs SET status='canceled' WHERE document_id=? AND status='queued'", (doc_id,))
        jid, now = db.uid(), time.time()
        c.execute('INSERT INTO jobs(id,document_id,status,total,options,created,updated) VALUES(?,?,?,?,?,?,?)',
                  (jid, doc_id, 'queued', doc['page_count'], db.dumps({'pages': selected, 'pipeline_version': PIPELINE_VERSION}), now, now))
        metadata = json.loads(doc['metadata'])
        metadata['pipeline_version'] = PIPELINE_VERSION
        c.execute("UPDATE documents SET status='queued',metadata=? WHERE id=?", (db.dumps(metadata), doc_id))
    return jid


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--pilot', action='store_true')
    p.add_argument('--document')
    p.add_argument('--pages', help='Comma-separated PDF page numbers')
    args = p.parse_args()
    db.init()
    docs = db.rows('SELECT * FROM documents' + (' WHERE id=?' if args.document else ''), (args.document,) if args.document else ())
    for doc in docs:
        pages = [int(n) for n in args.pages.split(',')] if args.pages else PILOT.get(doc['filename']) if args.pilot else None
        print(doc['filename'], reprocess(doc['id'], pages), flush=True)
