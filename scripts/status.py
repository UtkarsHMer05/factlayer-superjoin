"""Print a credential-free snapshot for operators and handoff agents."""
import json

from backend.factlayer import db
from backend.factlayer.config import PIPELINE_VERSION, settings

if __name__ == '__main__':
    db.init()
    print(json.dumps({'model': settings.model, 'pipeline_version': PIPELINE_VERSION,
        'claims': db.rows('SELECT status,count(*) count FROM claims GROUP BY status'),
        'relationships': db.rows('SELECT label,count(*) count FROM relationships GROUP BY label'),
        'jobs': db.rows('SELECT d.filename,j.status,j.progress,j.total,j.requests,j.tokens,j.message FROM jobs j JOIN documents d ON d.id=j.document_id WHERE j.id=(SELECT id FROM jobs WHERE document_id=d.id ORDER BY created DESC LIMIT 1)'),
        'recent_failures': db.rows('SELECT stage,message FROM failures ORDER BY created DESC LIMIT 5')}, indent=2))
