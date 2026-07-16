"""
Lexis — Database Layer

SQLite veritabanı bağlantısı ve tablo oluşturma işlemleri.
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable, Generator
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 3

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

# v3: her tekrarın kaydı. Kelimenin son hâli (last_reviewed_at) geçmişi
# tutmadığından streak ve aktivite grafiği için ayrı bir günlük gerekiyor.
CREATE_REVIEW_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS review_log (
    id            TEXT PRIMARY KEY,
    word_id       TEXT NOT NULL,
    grade         INTEGER NOT NULL,
    reviewed_at   TEXT NOT NULL,
    interval_days INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (word_id) REFERENCES words(id) ON DELETE CASCADE
);
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_words_term ON words(term COLLATE NOCASE);",
    "CREATE INDEX IF NOT EXISTS idx_words_language ON words(language);",
    "CREATE INDEX IF NOT EXISTS idx_words_status ON words(status);",
    "CREATE INDEX IF NOT EXISTS idx_words_created_at ON words(created_at DESC);",
    "CREATE INDEX IF NOT EXISTS idx_words_is_favorite ON words(is_favorite);",
    "CREATE INDEX IF NOT EXISTS idx_words_due_at ON words(due_at);",
    "CREATE INDEX IF NOT EXISTS idx_review_log_reviewed_at ON review_log(reviewed_at);",
    "CREATE INDEX IF NOT EXISTS idx_review_log_word_id ON review_log(word_id);",
]

CREATE_SCHEMA_VERSION = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);
"""


def _migrate_v2(conn: sqlite3.Connection) -> None:
    """v1 → v2: aralıklı tekrar (SM-2) sütunlarını ekler."""
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(words)")}
    for column, definition in WORDS_COLUMN_MIGRATIONS.items():
        if column not in existing:
            logger.info("Migration v2: words.%s sütunu ekleniyor", column)
            conn.execute(f"ALTER TABLE words ADD COLUMN {column} {definition}")


def _migrate_v3(conn: sqlite3.Connection) -> None:
    """v2 → v3: tekrar geçmişi tablosunu ekler (streak / aktivite grafiği için)."""
    logger.info("Migration v3: review_log tablosu oluşturuluyor")
    conn.execute(CREATE_REVIEW_LOG_TABLE)


# Sürüm anahtarlı migration zinciri: saklı sürümden SCHEMA_VERSION'a kadar
# sırayla uygulanır. Her adım idempotent olmalıdır.
MIGRATIONS: dict[int, Callable[[sqlite3.Connection], None]] = {
    2: _migrate_v2,
    3: _migrate_v3,
}


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

            is_new = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='words'").fetchone()[0] == 0

            conn.execute(CREATE_WORDS_TABLE)
            conn.execute(CREATE_SETTINGS_TABLE)
            conn.execute(CREATE_REVIEW_LOG_TABLE)

            self._run_migrations(conn, is_new=is_new)

            for index_sql in CREATE_INDEXES:
                conn.execute(index_sql)

            conn.commit()
        logger.info("Veritabanı hazır.")

    def _run_migrations(self, conn: sqlite3.Connection, is_new: bool) -> None:
        """
        Saklı şema sürümünden güncel sürüme kadar gereken adımları uygular.

        Yeni oluşturulan veritabanları zaten güncel şemayla kurulduğu için
        adımlar atlanır, yalnızca sürüm damgalanır.
        """
        row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
        current = row["version"] if row else (SCHEMA_VERSION if is_new else 1)

        if current < SCHEMA_VERSION:
            for version in range(current + 1, SCHEMA_VERSION + 1):
                step = MIGRATIONS.get(version)
                if step is not None:
                    step(conn)
            logger.info("Şema %d → %d yükseltildi.", current, SCHEMA_VERSION)

        if row is None:
            conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))
        elif row["version"] != SCHEMA_VERSION:
            conn.execute("DELETE FROM schema_version")
            conn.execute("INSERT INTO schema_version (version) VALUES (?)", (SCHEMA_VERSION,))

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
