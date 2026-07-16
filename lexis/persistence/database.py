"""
Lexis — Database Layer

SQLite veritabanı bağlantısı ve tablo oluşturma işlemleri.
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 2

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
    review_count      INTEGER NOT NULL DEFAULT 0,
    ease_factor       REAL NOT NULL DEFAULT 2.5,
    interval_days     INTEGER NOT NULL DEFAULT 0,
    repetitions       INTEGER NOT NULL DEFAULT 0,
    due_at            TEXT
);
"""

# v1 → v2 ile eklenen sütunlar (mevcut veritabanları için ALTER TABLE migration).
WORDS_COLUMN_MIGRATIONS: dict[str, str] = {
    "ease_factor": "REAL NOT NULL DEFAULT 2.5",
    "interval_days": "INTEGER NOT NULL DEFAULT 0",
    "repetitions": "INTEGER NOT NULL DEFAULT 0",
    "due_at": "TEXT",
}

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
    "CREATE INDEX IF NOT EXISTS idx_words_due_at ON words(due_at);",
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

            # Mevcut (eski) veritabanlarına yeni sütunları ekle.
            self._migrate_columns(conn)

            for index_sql in CREATE_INDEXES:
                conn.execute(index_sql)

            # Schema version kaydet / güncelle
            current = conn.execute(
                "SELECT version FROM schema_version LIMIT 1"
            ).fetchone()
            if current is None:
                conn.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (SCHEMA_VERSION,),
                )
            elif current["version"] != SCHEMA_VERSION:
                conn.execute("DELETE FROM schema_version")
                conn.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (SCHEMA_VERSION,),
                )
            conn.commit()
        logger.info("Veritabanı hazır.")

    def _migrate_columns(self, conn: sqlite3.Connection) -> None:
        """words tablosunda eksik olan sütunları ekler (idempotent)."""
        existing = {row["name"] for row in conn.execute("PRAGMA table_info(words)")}
        for column, definition in WORDS_COLUMN_MIGRATIONS.items():
            if column not in existing:
                logger.info("Migration: words.%s sütunu ekleniyor", column)
                conn.execute(f"ALTER TABLE words ADD COLUMN {column} {definition}")

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

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Tek bağlantı, tek commit ile atomik işlem.

        Toplu yazmalarda (örn. içe aktarma) her satır için ayrı bağlantı açıp
        commit etmek yerine kullanılır: hata hâlinde tamamı geri alınır.
        """
        with self.connection() as conn:
            yield conn
            conn.commit()

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
