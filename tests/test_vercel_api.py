from fastapi.testclient import TestClient
from api.index import app

client = TestClient(app)


def test_vercel_health():
    response = client.get('/api/health')
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert data['read_only'] is True


def test_vercel_health_root_fallback():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_vercel_index_py_fallback():
    response = client.get('/api/index.py')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_vercel_path_normalization_header():
    response = client.get('/api/index.py', headers={'x-vercel-matched-path': '/api/health'})
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'


def test_vercel_collections():
    response = client.get('/api/collections')
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]['name'] == 'Sample Financial Evidence Collection'


def test_vercel_facts():
    response = client.get('/api/collections/col-sample-demo/facts?status=accepted')
    assert response.status_code == 200
    data = response.json()
    assert 'items' in data
    assert data['total'] >= 1
    # Check search query
    search_res = client.get('/api/collections/col-sample-demo/facts?q=Margin')
    assert search_res.status_code == 200
    assert search_res.json()['total'] == 1


def test_vercel_relationships():
    response = client.get('/api/collections/col-sample-demo/relationships')
    assert response.status_code == 200
    data = response.json()
    assert 'items' in data
    assert data['total'] >= 1


def test_vercel_failures():
    response = client.get('/api/collections/col-sample-demo/failures')
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


def test_vercel_read_only_mutations():
    # Attempting to create collection or upload document returns 403 with clear explanation
    create_res = client.post('/api/collections', json={'name': 'test'})
    assert create_res.status_code == 403

    upload_res = client.post('/api/collections/col-sample-demo/documents')
    assert upload_res.status_code == 403


def test_vercel_catch_all():
    response = client.get('/api/unknown/endpoint')
    assert response.status_code == 200
    assert response.json() == []
