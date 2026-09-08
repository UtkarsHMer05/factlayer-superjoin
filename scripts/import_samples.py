"""Restore authentic exports; source PDFs must match their recorded SHA-256 hashes."""
import argparse
import gzip
import hashlib
import json
import time
import zipfile
from pathlib import Path

from backend.factlayer import db
from backend.factlayer.config import settings


def restore(export_path, archive):
    opener = gzip.open if str(export_path).endswith('.gz') else open
    with opener(export_path, 'rt') as stream:
        result = json.load(stream)
    if result.get('provenance') != 'actual_pipeline_output':
        raise ValueError('Only actual pipeline exports can be restored')
    with zipfile.ZipFile(archive) as z:
        sources = {hashlib.sha256(raw).hexdigest(): raw for name in z.namelist()
                   if name.lower().endswith('.pdf') for raw in [z.read(name)]}
    for doc in result['documents']:
        if doc['hash'] not in sources:
            raise ValueError(f"Matching source bytes unavailable: {doc['filename']}")
    cid = result['collection']['id']
    if db.one('SELECT id FROM collections WHERE id=?', (cid,)):
        raise ValueError('Collection already exists; restore into a fresh FACT_DATA_DIR')
    (settings.data_dir / 'pdfs').mkdir(parents=True, exist_ok=True)
    for doc in result['documents']:
        path = settings.data_dir / 'pdfs' / (doc['hash'] + '.pdf')
        path.write_bytes(sources[doc['hash']])
        doc['path'] = str(path.resolve())
        doc['status'] = 'partial' if doc['extracted_pages'] < doc['page_count'] else 'completed'
    with db.connect() as c:
        for table in ['collections', 'documents', 'pages', 'evidence', 'claims', 'relationships', 'registry', 'failures', 'runs']:
            records = [result['collection']] if table == 'collections' else result[table]
            columns = [r['name'] for r in c.execute(f'PRAGMA table_info({table})')]
            for record in records:
                vals = [db.dumps(record[k]) if isinstance(record[k], (dict, list)) else record[k] for k in columns]
                c.execute(f"INSERT INTO {table} ({','.join(columns)}) VALUES({','.join('?' for _ in columns)})", vals)
        for claim in result['claims']:
            if claim['status'] == 'accepted':
                c.execute('INSERT INTO claim_search VALUES(?,?,?,?,?)', (claim['id'], cid, claim['subject'], claim['predicate'], claim['data']['assertion']))
        for doc in result['documents']:
            c.execute('INSERT INTO jobs(id,document_id,status,progress,total,message,created,updated) VALUES(?,?,?,?,?,?,?,?)',
                      (db.uid(), doc['id'], doc['status'], doc['extracted_pages'], doc['page_count'], 'Restored actual saved results; coverage is unchanged.', time.time(), time.time()))
    return cid


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', default='starter-datasets.zip')
    parser.add_argument('exports', nargs='+', type=Path)
    args = parser.parse_args()
    db.init()
    for export_path in args.exports:
        print(restore(export_path, args.archive))
