import time

import pymupdf
from fastapi.testclient import TestClient

from backend.factlayer import db
from backend.factlayer.api import app
from backend.factlayer.ingest import ingest
from backend.factlayer.model import ModelUnavailable
from backend.factlayer.worker import claim_job, process


def pdf_bytes():
    with pymupdf.open() as pdf:
        p = pdf.new_page()
        p.insert_text((40, 40), 'Example company has an office.')
        return pdf.tobytes()


def collection():
    cid = db.uid()
    db.execute('INSERT INTO collections VALUES(?,?,?)', (cid, 'Example', time.time()))
    return cid


def test_api_upload_dedup_and_collection_isolation():
    with TestClient(app) as client:
        a = client.post('/api/collections', json={'name': 'A'}).json()['id']
        b = client.post('/api/collections', json={'name': 'B'}).json()['id']
        content = pdf_bytes()
        one = client.post(f'/api/collections/{a}/documents', files={'file': ('one.pdf', content)}).json()
        two = client.post(f'/api/collections/{a}/documents', files={'file': ('renamed.pdf', content)}).json()
        three = client.post(f'/api/collections/{b}/documents', files={'file': ('one.pdf', content)}).json()
        assert one['document_id'] == two['document_id'] and two['deduplicated']
        assert three['document_id'] != one['document_id']
        assert len(client.get(f'/api/collections/{a}/documents').json()) == 1


def test_invalid_pdf_and_unknown_page():
    with TestClient(app) as client:
        cid = collection()
        assert client.post(f'/api/collections/{cid}/documents', files={'file': ('bad.pdf', b'hello')}).status_code == 422
        r = ingest(cid, 'a.pdf', pdf_bytes())
        assert client.get(f'/api/documents/{r["document_id"]}/pages/99/image').status_code == 404
        assert client.get(f'/api/documents/{r["document_id"]}/pages/1/image').headers['content-type'] == 'image/png'


def test_worker_lease_prevents_duplicate_processing_and_recovers():
    r = ingest(collection(), 'a.pdf', pdf_bytes())
    first = claim_job('first')
    assert first['id'] == r['job_id']
    assert claim_job('second') is None
    db.execute('UPDATE jobs SET lease=? WHERE id=?', (time.time() - 1, r['job_id']))
    assert claim_job('second')['id'] == first['id']


def test_missing_model_still_preserves_page_evidence(monkeypatch):
    def unavailable(*a, **kw):
        raise ModelUnavailable('Model is not accessible')
    monkeypatch.setattr('backend.factlayer.worker.extract', unavailable)
    result = ingest(collection(), 'a.pdf', pdf_bytes())
    process(claim_job('worker'), 'worker')
    assert db.one('SELECT status FROM jobs WHERE id=?', (result['job_id'],))['status'] == 'partial'
    assert db.one('SELECT count(*) n FROM evidence')['n'] > 0
    assert db.one("SELECT count(*) n FROM failures WHERE stage='model_access'")['n'] == 1
    assert db.one('SELECT count(*) n FROM claims')['n'] == 0


def test_resume_only_partial_jobs():
    with TestClient(app) as client:
        r = ingest(collection(), 'a.pdf', pdf_bytes())
        assert client.post(f'/api/jobs/{r["job_id"]}/resume').status_code == 409
        db.execute("UPDATE jobs SET status='partial' WHERE id=?", (r['job_id'],))
        assert client.post(f'/api/jobs/{r["job_id"]}/resume').json()['status'] == 'queued'
