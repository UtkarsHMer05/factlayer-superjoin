"""SQLAlchemy manages SQLite connections; explicit SQL keeps the small schema inspectable."""
import json
import time
import uuid
from contextlib import contextmanager

from sqlalchemy import create_engine, event

from .config import settings

database_path = settings.data_dir / 'knowledge.sqlite'
if settings.read_only:
    if not database_path.is_file():
        raise RuntimeError(
            f'Read-only FactLayer data is missing at {database_path}. '
            'Include the saved demo data before deploying this mode.'
        )
    # SQLite's URI mode prevents Vercel's immutable function bundle from
    # attempting a journal, schema, or data write.
    engine = create_engine(
        f'sqlite+pysqlite:///file:{database_path.resolve()}?mode=ro&uri=true',
        connect_args={'timeout': 30},
    )
else:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f'sqlite:///{database_path}', connect_args={'timeout': 30})


@event.listens_for(engine, 'connect')
def configure(dbapi, _):
    dbapi.row_factory = __import__('sqlite3').Row
    dbapi.execute('PRAGMA foreign_keys=ON')
    dbapi.execute('PRAGMA busy_timeout=30000')


@contextmanager
def connect():
    c = engine.raw_connection()
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()


def uid():
    return uuid.uuid4().hex


def dumps(v):
    return json.dumps(v, ensure_ascii=False)


def rows(sql, args=()):
    with connect() as c:
        return [dict(r) for r in c.execute(sql, args).fetchall()]


def one(sql, args=()):
    result = rows(sql, args)
    return result[0] if result else None


def execute(sql, args=()):
    with connect() as c:
        c.execute(sql, args)


def init():
    if settings.read_only:
        return
    with connect() as c:
        c.execute('PRAGMA journal_mode=WAL')
        c.executescript('''
        CREATE TABLE IF NOT EXISTS collections(id TEXT PRIMARY KEY, name TEXT NOT NULL, created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS documents(
          id TEXT PRIMARY KEY, collection_id TEXT NOT NULL REFERENCES collections(id),
          hash TEXT NOT NULL, filename TEXT NOT NULL, path TEXT NOT NULL, page_count INTEGER NOT NULL,
          status TEXT NOT NULL DEFAULT 'queued', metadata TEXT NOT NULL DEFAULT '{}', created REAL NOT NULL,
          UNIQUE(collection_id, hash));
        CREATE TABLE IF NOT EXISTS jobs(
          id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id), status TEXT NOT NULL,
          progress INTEGER NOT NULL DEFAULT 0, total INTEGER NOT NULL, lease REAL NOT NULL DEFAULT 0,
          owner TEXT, message TEXT, options TEXT NOT NULL DEFAULT '{}', requests INTEGER NOT NULL DEFAULT 0,
          tokens INTEGER NOT NULL DEFAULT 0, created REAL NOT NULL, updated REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS pages(
          id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id), number INTEGER NOT NULL,
          width REAL NOT NULL, height REAL NOT NULL, rotation INTEGER NOT NULL, status TEXT NOT NULL,
          data TEXT NOT NULL, UNIQUE(document_id,number));
        CREATE TABLE IF NOT EXISTS evidence(
          id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id), page INTEGER NOT NULL,
          text TEXT NOT NULL, data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS claims(
          id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id),
          collection_id TEXT NOT NULL REFERENCES collections(id), page INTEGER NOT NULL,
          subject TEXT NOT NULL, predicate TEXT NOT NULL, status TEXT NOT NULL, data TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS claim_lookup ON claims(collection_id,subject,predicate);
        CREATE VIRTUAL TABLE IF NOT EXISTS claim_search USING fts5(id UNINDEXED, collection_id UNINDEXED, subject, predicate, assertion);
        CREATE TABLE IF NOT EXISTS relationships(
          id TEXT PRIMARY KEY, collection_id TEXT NOT NULL REFERENCES collections(id),
          left_id TEXT NOT NULL REFERENCES claims(id), right_id TEXT NOT NULL REFERENCES claims(id),
          label TEXT NOT NULL, data TEXT NOT NULL, UNIQUE(left_id,right_id));
        CREATE TABLE IF NOT EXISTS failures(
          id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id), page INTEGER,
          stage TEXT NOT NULL, message TEXT NOT NULL, data TEXT NOT NULL DEFAULT '{}', created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS runs(
          id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id), page INTEGER,
          input_hash TEXT NOT NULL, model TEXT NOT NULL, version TEXT NOT NULL, status TEXT NOT NULL,
          tokens INTEGER NOT NULL, duration REAL NOT NULL, data TEXT NOT NULL, created REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS registry(
          id TEXT PRIMARY KEY, collection_id TEXT NOT NULL REFERENCES collections(id), kind TEXT NOT NULL,
          label TEXT NOT NULL, data TEXT NOT NULL, UNIQUE(collection_id,kind,label));
        PRAGMA user_version=1;
        ''')


def failure(doc_id, page, stage, message, data=None):
    execute('INSERT INTO failures VALUES(?,?,?,?,?,?,?)',
            (uid(), doc_id, page, stage, message, dumps(data or {}), time.time()))


def unpack(row):
    if row is None:
        return None
    result = dict(row)
    for key in ('data', 'metadata', 'options'):
        if key in result:
            result[key] = json.loads(result[key])
    return result
