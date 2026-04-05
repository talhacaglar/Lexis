"""
Lexis — Word Repository

Kelime CRUD operasyonlarını kapsayan repository sınıfı.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from lexis.domain.exceptions import DatabaseError, WordNotFoundError
from lexis.domain.models import Word, WordStats, WordStatus
from lexis.persistence.database import Database

logger = logging.getLogger(__name__)


def _row_to_word(row) -> Word:
    """SQLite satırını Word domain nesnesine dönüştürür."""
    return Word(
        id=row["id"],
        term=row["term"],
        language=row["language"],
        definition=row["definition"],
        definition_short=row["definition_short"],
        synonyms=json.loads(row["synonyms"] or "[]"),
        antonyms=json.loads(row["antonyms"] or "[]"),
        example_sentences=json.loads(row["example_sentences"] or "[]"),
        usage_notes=row["usage_notes"] or "",
        part_of_speech=row["part_of_speech"] or "",
        status=WordStatus(row["status"]),
        is_favorite=bool(row["is_favorite"]),
        tags=json.loads(row["tags"] or "[]"),
        ai_generated=bool(row["ai_generated"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        last_reviewed_at=(
            datetime.fromisoformat(row["last_reviewed_at"])
            if row["last_reviewed_at"]
            else None
        ),
        review_count=row["review_count"],
    )


def _word_to_params(word: Word) -> dict:
    """Word nesnesini SQLite parametrelerine dönüştürür."""
    return {
        "id": word.id,
        "term": word.term,
        "language": word.language,
        "definition": word.definition,
        "definition_short": word.definition_short,
        "synonyms": json.dumps(word.synonyms, ensure_ascii=False),
        "antonyms": json.dumps(word.antonyms, ensure_ascii=False),
        "example_sentences": json.dumps(word.example_sentences, ensure_ascii=False),
        "usage_notes": word.usage_notes,
        "part_of_speech": word.part_of_speech,
        "status": word.status.value,
        "is_favorite": int(word.is_favorite),
        "tags": json.dumps(word.tags, ensure_ascii=False),
        "ai_generated": int(word.ai_generated),
        "created_at": word.created_at.isoformat(),
        "updated_at": word.updated_at.isoformat(),
        "last_reviewed_at": (
            word.last_reviewed_at.isoformat() if word.last_reviewed_at else None
        ),
        "review_count": word.review_count,
    }


class WordRepository:
    """Kelime CRUD operasyonları için repository."""

    def __init__(self, db: Database) -> None:
        self._db = db

    # ── Create ────────────────────────────────────────────────────────────

    def create(self, word: Word) -> Word:
        """Yeni kelime ekler."""
        try:
            params = _word_to_params(word)
            with self._db.connection() as conn:
                conn.execute(
                    """
                    INSERT INTO words (
                        id, term, language, definition, definition_short,
                        synonyms, antonyms, example_sentences, usage_notes,
                        part_of_speech, status, is_favorite, tags, ai_generated,
                        created_at, updated_at, last_reviewed_at, review_count
                    ) VALUES (
                        :id, :term, :language, :definition, :definition_short,
                        :synonyms, :antonyms, :example_sentences, :usage_notes,
                        :part_of_speech, :status, :is_favorite, :tags, :ai_generated,
                        :created_at, :updated_at, :last_reviewed_at, :review_count
                    )
                    """,
                    params,
                )
                conn.commit()
            logger.info(f"Kelime eklendi: {word.term} ({word.language})")
            return word
        except Exception as e:
            raise DatabaseError(f"Kelime eklenemedi: {word.term}", original=e) from e

    # ── Read ──────────────────────────────────────────────────────────────

    def get_by_id(self, word_id: str) -> Word:
        """ID'ye göre kelime getirir."""
        with self._db.connection() as conn:
            row = conn.execute(
                "SELECT * FROM words WHERE id = ?", (word_id,)
            ).fetchone()
        if not row:
            raise WordNotFoundError(word_id)
        return _row_to_word(row)

    def get_all(
        self,
        search: str = "",
        language: str = "",
        status: Optional[WordStatus] = None,
        favorites_only: bool = False,
        tag: str = "",
        sort_by: str = "created_at",
        sort_desc: bool = True,
        limit: int = 0,
        offset: int = 0,
    ) -> list[Word]:
        """Filtrelenmiş ve sıralanmış kelime listesi döndürür."""
        conditions = []
        params: list = []

        if search:
            conditions.append("(term LIKE ? OR definition LIKE ?)")
            like = f"%{search}%"
            params.extend([like, like])

        if language:
            conditions.append("language = ?")
            params.append(language)

        if status:
            conditions.append("status = ?")
            params.append(status.value)

        if favorites_only:
            conditions.append("is_favorite = 1")

        if tag:
            conditions.append("tags LIKE ?")
            params.append(f'%"{tag}"%')

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        # Güvenli sıralama sütunu
        valid_sorts = {"created_at", "updated_at", "term", "review_count"}
        sort_col = sort_by if sort_by in valid_sorts else "created_at"
        order = "DESC" if sort_desc else "ASC"

        sql = f"SELECT * FROM words {where_clause} ORDER BY {sort_col} {order}"

        if limit > 0:
            sql += f" LIMIT {limit}"
            if offset > 0:
                sql += f" OFFSET {offset}"

        with self._db.connection() as conn:
            rows = conn.execute(sql, params).fetchall()

        return [_row_to_word(r) for r in rows]

    def exists(self, term: str, language: str) -> bool:
        """Belirtilen kelime ve dil kombinasyonu mevcut mu kontrol eder."""
        with self._db.connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM words WHERE term = ? AND language = ? LIMIT 1",
                (term, language),
            ).fetchone()
        return row is not None

    def get_recent(self, limit: int = 12) -> list[Word]:
        """En son eklenen kelimeleri döndürür."""
        return self.get_all(sort_by="created_at", sort_desc=True, limit=limit)

    def get_recently_reviewed(self, limit: int = 6) -> list[Word]:
        """Son çalışılan kelimeleri döndürür."""
        with self._db.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM words
                WHERE last_reviewed_at IS NOT NULL
                ORDER BY last_reviewed_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [_row_to_word(r) for r in rows]

    def get_all_tags(self) -> list[str]:
        """Kullanılan tüm benzersiz etiketleri döndürür."""
        with self._db.connection() as conn:
            rows = conn.execute("SELECT tags FROM words WHERE tags != '[]'").fetchall()
        all_tags: set[str] = set()
        for row in rows:
            tags = json.loads(row["tags"])
            all_tags.update(tags)
        return sorted(all_tags)

    def get_stats(self) -> WordStats:
        """Genel istatistikleri döndürür."""
        today = datetime.utcnow().date().isoformat()
        with self._db.connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
            new = conn.execute(
                "SELECT COUNT(*) FROM words WHERE status = 'new'"
            ).fetchone()[0]
            learning = conn.execute(
                "SELECT COUNT(*) FROM words WHERE status = 'learning'"
            ).fetchone()[0]
            learned = conn.execute(
                "SELECT COUNT(*) FROM words WHERE status = 'learned'"
            ).fetchone()[0]
            needs_review = conn.execute(
                "SELECT COUNT(*) FROM words WHERE status = 'needs_review'"
            ).fetchone()[0]
            favorites = conn.execute(
                "SELECT COUNT(*) FROM words WHERE is_favorite = 1"
            ).fetchone()[0]
            added_today = conn.execute(
                "SELECT COUNT(*) FROM words WHERE created_at LIKE ?",
                (f"{today}%",),
            ).fetchone()[0]
            reviewed_today = conn.execute(
                "SELECT COUNT(*) FROM words WHERE last_reviewed_at LIKE ?",
                (f"{today}%",),
            ).fetchone()[0]

        return WordStats(
            total=total,
            new=new,
            learning=learning,
            learned=learned,
            needs_review=needs_review,
            favorites=favorites,
            added_today=added_today,
            reviewed_today=reviewed_today,
        )

    # ── Update ────────────────────────────────────────────────────────────

    def update(self, word: Word) -> Word:
        """Mevcut kelimeyi günceller."""
        word.updated_at = datetime.utcnow()
        try:
            params = _word_to_params(word)
            with self._db.connection() as conn:
                conn.execute(
                    """
                    UPDATE words SET
                        term = :term,
                        language = :language,
                        definition = :definition,
                        definition_short = :definition_short,
                        synonyms = :synonyms,
                        antonyms = :antonyms,
                        example_sentences = :example_sentences,
                        usage_notes = :usage_notes,
                        part_of_speech = :part_of_speech,
                        status = :status,
                        is_favorite = :is_favorite,
                        tags = :tags,
                        ai_generated = :ai_generated,
                        updated_at = :updated_at,
                        last_reviewed_at = :last_reviewed_at,
                        review_count = :review_count
                    WHERE id = :id
                    """,
                    params,
                )
                conn.commit()
            logger.info(f"Kelime güncellendi: {word.term}")
            return word
        except Exception as e:
            raise DatabaseError(f"Kelime güncellenemedi: {word.id}", original=e) from e

    # ── Delete ────────────────────────────────────────────────────────────

    def delete(self, word_id: str) -> None:
        """Kelimeyi siler."""
        with self._db.connection() as conn:
            conn.execute("DELETE FROM words WHERE id = ?", (word_id,))
            conn.commit()
        logger.info(f"Kelime silindi: {word_id}")

    def delete_all(self) -> int:
        """Tüm kelimeleri siler. Silinen sayısını döndürür."""
        with self._db.connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
            conn.execute("DELETE FROM words")
            conn.commit()
        return count
