"""Export actual database results. Does not synthesize or approve sample claims."""
from pathlib import Path

from backend.factlayer import db
from backend.factlayer.api import export

if __name__ == '__main__':
    db.init()
    out = Path('samples/actual-runs')
    out.mkdir(parents=True, exist_ok=True)
    for c in db.rows('SELECT id,name FROM collections'):
        target = out / (c['id'] + '.json')
        target.write_bytes(export(c['id']).body)
        print(c['name'], target)
