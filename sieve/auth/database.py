"""SQLite storage for Sieve authentication and audit records."""
from __future__ import annotations
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def database_path() -> Path:
    configured = os.environ.get("SIEVE_AUTH_DB_PATH", "").strip()
    path = Path(configured).expanduser() if configured else ROOT / "data" / "sieve_auth.db"
    if not path.is_absolute():
        path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path

def connect() -> sqlite3.Connection:
    db = sqlite3.connect(database_path(), timeout=30)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("PRAGMA journal_mode = WAL")
    return db

def init_db() -> None:
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            display_name TEXT NOT NULL,
            role TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            must_change_password INTEGER NOT NULL DEFAULT 1,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_login TEXT
        );
        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            event TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_events(created_at);
        CREATE INDEX IF NOT EXISTS idx_audit_username ON audit_events(username);
        """)
