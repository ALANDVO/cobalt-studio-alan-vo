"""SQLite connection helpers. Each call opens its own connection."""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  purpose TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS resolutions (
  id INTEGER PRIMARY KEY,
  project_id INTEGER NOT NULL REFERENCES projects(id),
  source TEXT NOT NULL,
  requested TEXT NOT NULL,
  status TEXT NOT NULL,
  matched TEXT,
  caller_exit_code INTEGER NOT NULL,
  explanation TEXT NOT NULL,
  matches_json TEXT NOT NULL,
  ignored_json TEXT NOT NULL,
  installed_json TEXT NOT NULL,
  node_version TEXT NOT NULL,
  nvmrc TEXT NOT NULL,
  package_json TEXT NOT NULL,
  lts_snapshot TEXT NOT NULL,
  lts_latest_codename TEXT NOT NULL,
  lts_latest_major INTEGER NOT NULL,
  binary_info_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY,
  action TEXT NOT NULL,
  entity TEXT NOT NULL,
  entity_id INTEGER NOT NULL,
  detail TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_resolutions_project ON resolutions(project_id, id);
"""


def default_database_path() -> str:
    configured = os.environ.get("COBALT_DATABASE_PATH", "").strip()
    if configured:
        return configured
    backend_dir = Path(__file__).resolve().parents[2]
    return str(backend_dir / "data" / "cobalt.sqlite")


def connect(path: str) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def session(path: str) -> Iterator[sqlite3.Connection]:
    connection = connect(path)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db(path: str) -> None:
    with session(path) as connection:
        connection.executescript(SCHEMA)
