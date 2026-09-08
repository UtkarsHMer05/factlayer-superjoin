"""Sample selection belongs here, never in runtime extraction code."""
import argparse
import time
import zipfile

from backend.factlayer import db
from backend.factlayer.ingest import ingest

PILOT = {
    '01-delhivery-prospectus-2022-excerpt.pdf': [30],
    '02-delhivery-annual-report-fy24-excerpt.pdf': [2, 22, 31, 51, 68],
    '03-delhivery-q4-fy24-earnings-presentation.pdf': [8, 9, 17],
    '01-india-economic-survey-2024-25-excerpt.pdf': [14, 28],
    '02-rbi-annual-report-2024-25-excerpt.pdf': [8, 9],
    '03-imf-india-2025-article-iv-excerpt.pdf': [3, 5],
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--full', action='store_true', help='Process all 511 pages; default is a disclosed 15-page pilot.')
    args = parser.parse_args()
    db.init()
    with zipfile.ZipFile('starter-datasets.zip') as archive:
        for name in archive.namelist():
            if not name.endswith('.pdf'):
                continue
            collection = name.split('/')[1]
            old = db.one('SELECT id FROM collections WHERE name=?', (collection,))
            cid = old['id'] if old else db.uid()
            if not old:
                db.execute('INSERT INTO collections VALUES(?,?,?)', (cid, collection, time.time()))
            filename = name.split('/')[-1]
            result = ingest(cid, filename, archive.read(name), {} if args.full else {'pages': PILOT[filename]})
            print(filename, result, flush=True)


if __name__ == '__main__':
    main()
