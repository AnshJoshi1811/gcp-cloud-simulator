"""SQLite-backed state store mapping AWS resource ids to Docker resources.

Lets `minicloud status`/`destroy-all` work even before (or without) a fresh
Docker reconciliation pass, and survives server restarts.
"""

import contextlib
import sqlite3
import threading
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

DB_PATH = os.environ.get("MINICLOUD_DB_PATH", os.path.join(os.getcwd(), "minicloud.db"))

_lock = threading.Lock()


@contextlib.contextmanager
def _connect():
    # sqlite3.Connection's own context manager only commits/rolls back on
    # exit, it does NOT close the connection — without an explicit close()
    # each call leaks a connection/file handle, which on Windows blocks
    # later attempts to delete the DB file. Wrap it so callers get both.
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def init_db():
    with _lock, _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS resources (
                resource_id TEXT PRIMARY KEY,
                resource_type TEXT NOT NULL,
                docker_id TEXT,
                docker_name TEXT,
                extra TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )


def upsert_resource(
    resource_id: str, resource_type: str, docker_id: Optional[str] = None,
    docker_name: Optional[str] = None, extra: str = "",
):
    now = datetime.now(timezone.utc).isoformat()
    with _lock, _connect() as conn:
        conn.execute(
            """
            INSERT INTO resources (resource_id, resource_type, docker_id, docker_name, extra, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(resource_id) DO UPDATE SET
                docker_id=excluded.docker_id,
                docker_name=excluded.docker_name,
                extra=excluded.extra,
                updated_at=excluded.updated_at
            """,
            (resource_id, resource_type, docker_id, docker_name, extra, now, now),
        )


def get_resource(resource_id: str) -> Optional[Dict]:
    with _lock, _connect() as conn:
        row = conn.execute("SELECT * FROM resources WHERE resource_id = ?", (resource_id,)).fetchone()
        return dict(row) if row else None


def list_resources(resource_type: Optional[str] = None) -> List[Dict]:
    with _lock, _connect() as conn:
        if resource_type:
            rows = conn.execute("SELECT * FROM resources WHERE resource_type = ?", (resource_type,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM resources").fetchall()
        return [dict(r) for r in rows]


def delete_resource(resource_id: str):
    with _lock, _connect() as conn:
        conn.execute("DELETE FROM resources WHERE resource_id = ?", (resource_id,))


def clear_all():
    with _lock, _connect() as conn:
        conn.execute("DELETE FROM resources")
