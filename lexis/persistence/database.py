"""
Lexis — Database Layer

SQLite veritabanı bağlantısı ve tablo oluşturma işlemleri.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1

CREATE_WORDS_TABLE = """
CREATE TABLE IF NOT EXISTS words (
    id                TEXT PRIMARY KEY,
    term              TEXT NOT NULL,
    language          TEXT NOT NULL DEFAULT 'en',
    definition        TEXT NOT NULL DEFAULT '',
    definition_short  TEXT NOT NULL DEFAULT '',
    synonyms          TEXT NOT NULL DEFAULT '[]',
    antonyms          TEXT NOT NULL DEFAULT '[]',
    example_sentences TEXT NOT NULL DEFAULT '[]',
    usage_notes       TEXT NOT NULL DEFAULT '',
    part_of_speech    TEXT NOT NULL DEFAULT '',
    status            TEXT NOT NULL DEFAULT 'new',
    is_favorite       INTEGER NOT NULL DEFAULT 0,
    tags              TEXT NOT NULL DEFAULT '[]',
    ai_generated      INTEGER NOT NULL DEFAULT 1,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL,
    last_reviewed_at  TEXT,
    review_count      INTEGER NOT NULL DEFAULT 0
);
"""

CREATE_SETTINGS_TABLE = """
CREATE TABLE IF NOT EXISTS app_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_words_term ON words(term COLLATE NOCASE);",
    "CREATE INDEX IF NOT EXISTS idx_words_language ON words(language);",
    "CREATE INDEX IF NOT EXISTS idx_words_status ON words(status);",
    "CREATE INDEX IF NOT EXISTS idx_words_created_at ON words(created_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_words_is_favorite ON words(is_favorite);",
]

CREATE_SCHEMA_VERSION = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);
"""


class Database:
    """SQLite veritabanı yöneticisi."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._initialize()

    def _initialize(self) -> None:
        """Tabloları oluşturur ve gerekirse migration uygular."""
        logger.info(f"Veritabanı başlatılıyor: {self.db_path}")
        with self.connection() as conn:
            conn.execute(CREATE_SCHEMA_VERSION)
            conn.execute(CREATE_WORDS_TABLE)
            conn.execute(CREATE_SETTINGS_TABLE)
            for index_sql in CREATE_INDEXES:
                conn.execute(index_sql)

            # Schema version kaydet
            current = conn.execute(
                "SELECT version FROM schema_version LIMIT 1"
            ).fetchone()
            if current is None:
                conn.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (SCHEMA_VERSION,),
                )
            conn.commit()
        logger.info("Veritabanı hazır.")

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager ile güvenli veritabanı bağlantısı."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def get_setting(self, key: str, default: str = "") -> str:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT value FROM app_settings WHERE key = ?", (key,)
            ).fetchone()
            return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self.connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)",
                (key, value),
            )
            conn.commit()
