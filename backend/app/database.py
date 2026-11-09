import sqlite3
from contextlib import contextmanager
from pathlib import Path

from flask import current_app

SCHEMA = """
CREATE TABLE IF NOT EXISTS repositories (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    path            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    first_opened_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_opened_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Created now, filled in by later phases (analysis history).
CREATE TABLE IF NOT EXISTS analysis_history (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_id     INTEGER NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    analyzed_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    total_commits     INTEGER NOT NULL,
    contributor_count INTEGER NOT NULL,
    branch_count      INTEGER NOT NULL,
    quality_score     REAL
);
"""


def init_db(app):
    """Create the database file and tables if they don't exist yet."""
    db_path = Path(app.config["DATABASE_PATH"])
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


@contextmanager
def get_db():
    """Open a connection, commit on success, roll back on error, always close."""
    conn = sqlite3.connect(current_app.config["DATABASE_PATH"])
    conn.row_factory = sqlite3.Row  # lets us read columns by name
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def upsert_repository(db, path, name):
    """Insert the repository if it is new, then return its id."""
    db.execute(
        """
        INSERT INTO repositories (path, name) VALUES (?, ?)
        ON CONFLICT(path) DO UPDATE SET name = excluded.name
        """,
        (path, name),
    )
    return db.execute("SELECT id FROM repositories WHERE path = ?", (path,)).fetchone()["id"]