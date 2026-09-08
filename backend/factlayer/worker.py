"""Run with python -m backend.factlayer.worker. Jobs and page checkpoints survive restart."""
import hashlib
import json
import logging
import threading
import time

import pymupdf

from . import db
from .compare import key, relate_document
from .config import PIPELINE_VERSION, settings
from .model import ModelUnavailable, extract, job_context, verify
from .pdf import ground, page_units

log = logging.getLogger(__name__)


def claim_job(owner):
    now = time.time()
    with db.connect() as c:
        c.execute('BEGIN IMMEDIATE')
        row = c.execute("SELECT * FROM jobs WHERE status='queued' OR (status IN ('parsing','extracting','comparing') AND lease<?) ORDER BY created LIMIT 1", (now,)).fetchone()
        if row is None:
            return None
        c.execute("UPDATE jobs SET status='parsing',owner=?,lease=?,updated=? WHERE id=?", (owner, now + 90, now, row['id']))
        return dict(row)


def persist_claim(doc, page, candidate, units, verification=None):
    claim_id = hashlib.sha256((PIPELINE_VERSION + settings.model + doc['id'] + str(page) + candidate.model_dump_json()).encode()).hexdigest()[:32]
    if db.one('SELECT id FROM claims WHERE id=?', (claim_id,)):
        return
    try:
        data = ground(candidate, units)
        if verification is None or verification.get('valid') is not True:
            raise ValueError('Semantic verification: ' + (verification or {}).get('reason', 'No affirmative verification returned'))
        data['verification'] = verification
        status = 'accepted'
    except ValueError as exc:
        status = 'quarantined'
        data = candidate.model_dump()
        data['rejection'] = str(exc)
        db.failure(doc['id'], page, 'grounding', str(exc), {'claim_id': claim_id, 'assertion': candidate.assertion})
    data['id'] = claim_id
    data['model'] = settings.model
    data['pipeline_version'] = PIPELINE_VERSION
    with db.connect() as c:
        c.execute('INSERT INTO claims VALUES(?,?,?,?,?,?,?,?)',
                  (claim_id, doc['id'], doc['collection_id'], page, key(candidate.subject), key(candidate.predicate), status, db.dumps(data)))
        if status == 'accepted':
            c.execute('INSERT INTO claim_search VALUES(?,?,?,?,?)', (claim_id, doc['collection_id'], key(candidate.subject), key(candidate.predicate), candidate.assertion))
            for kind, label in [('entity', candidate.subject), ('predicate', candidate.predicate)]:
                c.execute('INSERT OR IGNORE INTO registry VALUES(?,?,?,?,?)',
                          (db.uid(), doc['collection_id'], kind, label, db.dumps({'evidence_claim': claim_id, 'aliases': [], 'method': 'observed'})))


def process(job, owner):
    doc = db.one('SELECT * FROM documents WHERE id=?', (job['document_id'],))
    options = json.loads(job['options'])
    selected = set(options.get('pages', []))
    metadata = json.loads(doc['metadata'])
    stopped = threading.Event()
    budget_context = job_context.set(job['id'])

    def heartbeat():
        while not stopped.wait(20):
            db.execute('UPDATE jobs SET lease=?,updated=? WHERE id=? AND owner=?', (time.time() + 90, time.time(), job['id'], owner))

    threading.Thread(target=heartbeat, daemon=True).start()
    started = time.monotonic()
    partial = bool(selected)
    blocked = False
    requests, tokens = job['requests'], job['tokens']
    try:
        db.execute("UPDATE documents SET status='processing' WHERE id=?", (doc['id'],))
        with pymupdf.open(doc['path']) as pdf:
            identity_units = []
            for ni in range(min(3, len(pdf))):
                identity_units.extend(page_units(pdf[ni], doc['id'], ni + 1)['units'])
            metadata = {'source_identity': [{'unit_id': u['id'], 'text': u['text'][:6000]} for u in identity_units]}
            for unit in identity_units:
                db.execute('INSERT OR REPLACE INTO evidence VALUES(?,?,?,?,?)', (unit['id'], doc['id'], unit['page'], unit['text'], db.dumps(unit)))
            for index, page in enumerate(pdf):
                number = index + 1
                existing = db.one('SELECT * FROM pages WHERE document_id=? AND number=?', (doc['id'], number))
                if existing and existing['status'] in ('extracted', 'empty'):
                    continue
                try:
                    parsed = page_units(page, doc['id'], number)
                    units = parsed.pop('units')
                    with db.connect() as c:
                        c.execute('INSERT INTO pages VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(document_id,number) DO UPDATE SET data=excluded.data,status=excluded.status',
                                  (db.uid(), doc['id'], number, parsed['width'], parsed['height'], parsed['rotation'], 'parsed', db.dumps(parsed)))
                        for unit in units:
                            c.execute('INSERT OR REPLACE INTO evidence VALUES(?,?,?,?,?)', (unit['id'], doc['id'], number, unit['text'], db.dumps(unit)))
                    for warning in parsed['warnings']:
                        if not existing:
                            db.failure(doc['id'], number, 'layout', warning, {'handling': 'Source page retained. Claims still require exact anchors; complex charts need visual review.'})
                    if selected and number not in selected:
                        continue
                    if not units:
                        db.execute("UPDATE pages SET status='empty' WHERE document_id=? AND number=?", (doc['id'], number))
                        continue
                    usage = db.one('SELECT requests,tokens FROM jobs WHERE id=?', (job['id'],))
                    requests, tokens = usage['requests'], usage['tokens']
                    if blocked or (settings.max_requests and requests >= settings.max_requests) or (settings.max_tokens and tokens >= settings.max_tokens):
                        partial = True
                        continue
                    db.execute("UPDATE jobs SET status='extracting',message=?,updated=? WHERE id=?", (f'Extracting PDF page {number} of {len(pdf)}', time.time(), job['id']))
                    # Each unit is one small model request; the compact prompt needs short sources.
                    for unit in units:
                        if settings.max_requests and requests >= settings.max_requests:
                            partial = True
                            break
                        reference_units = [unit, *identity_units]
                        output, metrics = extract(doc['id'], number, [unit], metadata)
                        requests += metrics.get('requests', 0 if metrics.get('cached') else 1)
                        tokens += metrics['tokens']
                        if output.claims:
                            decisions, verification_metrics = verify(doc['id'], number, output.claims, [unit], metadata)
                            requests += 1
                            tokens += verification_metrics['tokens']
                        else:
                            decisions, verification_metrics = {}, {'tokens': 0}
                        for ci, candidate in enumerate(output.claims):
                            persist_claim(doc, number, candidate, reference_units, decisions.get(ci))
                        for warning in output.warnings:
                            db.failure(doc['id'], number, 'extraction', warning)
                    db.execute("UPDATE pages SET status='extracted' WHERE document_id=? AND number=?", (doc['id'], number))
                    db.execute('UPDATE jobs SET requests=?,tokens=? WHERE id=?', (requests, tokens, job['id']))

                except ModelUnavailable as exc:
                    db.failure(doc['id'], number, 'model_access', str(exc))
                    blocked = True
                    partial = True
                except Exception as exc:
                    log.exception('Page processing failed')
                    db.failure(doc['id'], number, 'processing', str(exc)[:500])
                    partial = True
                finally:
                    processed = db.one("SELECT COUNT(*) AS n FROM pages WHERE document_id=? AND status IN ('extracted','empty')", (doc['id'],))['n']
                    db.execute('UPDATE jobs SET progress=?,updated=? WHERE id=?', (processed, time.time(), job['id']))
        db.execute("UPDATE jobs SET status='comparing' WHERE id=?", (job['id'],))
        relate_document(doc['id'])
        waiting = db.one("SELECT j.id FROM jobs j JOIN documents d ON d.id=j.document_id WHERE d.collection_id=? AND j.id!=? AND j.status IN ('queued','parsing','extracting','comparing') LIMIT 1", (doc['collection_id'], job['id']))
        if not blocked and not waiting:
            try:
                from .alignment import reconcile
                reconcile(doc['collection_id'])
            except Exception as exc:
                log.exception('Semantic comparison failed')
                db.failure(doc['id'], None, 'comparison', str(exc)[:500])
                partial = True
        status = 'partial' if partial else 'completed'
        message = ('Model unavailable; source parsing completed. Configure access and resume.' if blocked else
                   'Selected pages or budget limit; remaining pages are available to resume.' if partial else 'Processing complete.')
        message += f' Elapsed {time.monotonic() - started:.1f}s.'
        db.execute('UPDATE jobs SET status=?,message=?,lease=0,updated=? WHERE id=?', (status, message, time.time(), job['id']))
        db.execute('UPDATE documents SET status=? WHERE id=?', (status, doc['id']))
    finally:
        stopped.set()
        job_context.reset(budget_context)


def main():
    logging.basicConfig(level=logging.INFO)
    db.init()
    owner = db.uid()
    while True:
        job = claim_job(owner)
        if job:
            try:
                process(job, owner)
            except Exception as exc:
                log.exception('Job failed')
                db.execute("UPDATE jobs SET status='failed',message=?,lease=0 WHERE id=?", (str(exc)[:500], job['id']))
                db.execute("UPDATE documents SET status='failed' WHERE id=?", (job['document_id'],))
        else:
            time.sleep(1)


if __name__ == '__main__':
    main()
