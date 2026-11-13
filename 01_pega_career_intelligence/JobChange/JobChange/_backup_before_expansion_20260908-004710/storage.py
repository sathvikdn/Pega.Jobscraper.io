"""Local SQLite persistence. Every call owns its connection for safe thread use."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE IF NOT EXISTS records (kind TEXT NOT NULL, id TEXT NOT NULL, payload TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(kind,id))')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def put(self, kind, key, payload):
        with self.connect() as db:
            db.execute('INSERT INTO records VALUES (?,?,?,?) ON CONFLICT(kind,id) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at',
                       (kind, key, json.dumps(payload, ensure_ascii=False), now()))

    def get(self, kind, key, default=None):
        with self.connect() as db:
            row = db.execute('SELECT payload FROM records WHERE kind=? AND id=?', (kind,key)).fetchone()
        return json.loads(row[0]) if row else default

    def all(self, kind):
        with self.connect() as db:
            rows = db.execute('SELECT id,payload FROM records WHERE kind=? ORDER BY updated_at DESC', (kind,)).fetchall()
        return {key:json.loads(payload) for key,payload in rows}
