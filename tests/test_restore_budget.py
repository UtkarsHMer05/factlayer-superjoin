import gzip
import json
import zipfile

import pytest
from fastapi.testclient import TestClient

from backend.factlayer import db, model
from backend.factlayer.api import app, export
from backend.factlayer.config import settings
from backend.factlayer.ingest import ingest
from scripts.import_samples import restore
from scripts.reprocess import reprocess
from tests.test_api_jobs import collection, pdf_bytes


def test_saved_results_require_identical_pdf_and_restore(tmp_path):
    cid = collection()
    raw = pdf_bytes()
    ingest(cid, 'source.pdf', raw)
    artifact = tmp_path / 'export.json.gz'
    with gzip.open(artifact, 'wb') as f:
        f.write(export(cid).body)
    archive = tmp_path / 'sources.zip'
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('source.pdf', b'wrong bytes')
    with pytest.raises(ValueError, match='Matching source bytes'):
        restore(artifact, archive)
    with zipfile.ZipFile(archive, 'w') as z:
        z.writestr('source.pdf', raw)
    with db.connect() as c:
        for table in ['jobs', 'documents', 'collections']:
            c.execute(f'DELETE FROM {table}')
    assert restore(artifact, archive) == cid
    assert db.one('SELECT status FROM documents')['status'] == 'partial'
    assert db.one('SELECT status FROM jobs')['status'] == 'partial'


def test_every_http_attempt_reserves_budget_before_network(monkeypatch):
    r = ingest(collection(), 'source.pdf', pdf_bytes())
    monkeypatch.setattr(settings, 'max_requests', 1)
    token = model.job_context.set(r['job_id'])
    try:
        model.reserve_request()
        with pytest.raises(model.ModelUnavailable, match='budget'):
            model.reserve_request()
        assert db.one('SELECT requests FROM jobs')['requests'] == 1
    finally:
        model.job_context.reset(token)


def test_reprocess_rejects_active_lease_and_out_of_range():
    r = ingest(collection(), 'source.pdf', pdf_bytes())
    with pytest.raises(ValueError, match='outside'):
        reprocess(r['document_id'], [2])
    jid = reprocess(r['document_id'], [1])
    assert json.loads(db.one('SELECT options FROM jobs WHERE id=?', (jid,))['options'])['pages'] == [1]
    assert db.one('SELECT status FROM jobs WHERE id=?', (r['job_id'],))['status'] == 'canceled'


def test_sample_mode_disables_extraction(monkeypatch):
    r = ingest(collection(), 'source.pdf', pdf_bytes())
    monkeypatch.setattr(settings, 'sample_mode', True)
    with TestClient(app) as client:
        assert client.get('/api/health').json()['mode'] == 'sample'
        assert client.post(f"/api/jobs/{r['job_id']}/resume").status_code == 403
        assert client.post('/api/collections/any/documents', files={'file': ('a.pdf', pdf_bytes())}).status_code == 403
