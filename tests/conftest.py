import os
import tempfile

import pytest

_test_dir = tempfile.TemporaryDirectory(prefix='factlayer-tests-')
os.environ['FACT_DATA_DIR'] = _test_dir.name

from backend.factlayer import db


@pytest.fixture(autouse=True)
def clean_db():
    db.init()
    with db.connect() as c:
        for table in ['relationships', 'claim_search', 'claims', 'registry', 'evidence', 'pages', 'failures', 'runs', 'jobs', 'documents', 'collections']:
            c.execute(f'DELETE FROM {table}')
    yield
