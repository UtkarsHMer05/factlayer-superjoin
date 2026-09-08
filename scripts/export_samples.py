"""Export actual database results. Does not synthesize or approve sample claims."""
import gzip
from pathlib import Path

from backend.factlayer import db
from backend.factlayer.api import export

if __name__ == '__main__':
    db.init()
    out = Path('samples/actual-runs')
    out.mkdir(parents=True, exist_ok=True)
    for c in db.rows('SELECT id,name FROM collections'):
        target = out / (c['id'] + '.json.gz')
        with gzip.open(target, 'wb') as stream:
            stream.write(export(c['id']).body)
        print(c['name'], target)
