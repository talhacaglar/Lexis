"""
Lexis — Word Repository

Kelime CRUD operasyonlarını kapsayan repository sınıfı.
"""

from __future__ import annotations

import functools
import json
import logging
import uuid
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from datetime import time as dtime
from typing import TypeVar

from lexis.domain.exceptions import DatabaseError, LexisError, WordNotFoundError
from lexis.domain.models import Word, WordStats, WordStatus, utcnow
from lexis.persistence.database import Database

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _wrap_db_errors(message: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Ham sqlite3 hatalarını DatabaseError'a sarmalar; domain hataları
    (WordNotFoundError gibi) olduğu gibi çağırana geçer.
    """

    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs) -> T:
            try:
                return fn(*args, **kwargs)
            except LexisError:
                raise
            except Exception as e:
                raise DatabaseError(message, original=e) from e

        return wrapper

    return decorator


def _iso_utc(dt: datetime | None) -> str | None:
    """
    Zaman damgasını UTC'ye normalize ederek ISO-8601 string'e çevirir.

    Tüm zaman damgaları aynı ofsetle (+00:00) saklandığında sözlüksel string
    karşılaştırması kronolojik sıralamayla örtüşür; istatistik sorguları buna
    dayanır. Naive datetime'lar UTC kabul edilir.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat()


def _local_day_bounds_utc() -> tuple[str, str]:
    """
    İçinde bulunulan yerel günün [başlangıç, bitiş) sınırlarını UTC ISO string
    olarak döndürür. Zaman damgaları UTC saklandığı için "bugün" sayımları
    kullanıcının yerel gününe göre yapılabilsin diye gerekir.
    """
    now_local = datetime.now().astimezone()
    start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=1)
    return (
        start_local.astimezone(timezone.utc).isoformat(),
        end_local.astimezone(timezone.utc).isoformat(),
    )


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
        phonetic=row["phonetic"] or "",
        audio_url=row["audio_url"] or "",
        status=WordStatus(row["status"]),
        is_favorite=bool(row["is_favorite"]),
        tags=json.loads(row["tags"] or "[]"),
        ai_generated=bool(row["ai_generated"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        last_reviewed_at=(
            datetime.fromisoformat(row["last_reviewed_at"]) if row["last_reviewed_at"] else None
        ),
        review_count=row["review_count"],
        ease_factor=row["ease_factor"],
        interval_days=row["interval_days"],
        repetitions=row["repetitions"],
        due_at=datetime.fromisoformat(row["due_at"]) if row["due_at"] else None,
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
        "phonetic": word.phonetic,
        "audio_url": word.audio_url,
        "status": word.status.value,
        "is_favorite": int(word.is_favorite),
        "tags": json.dumps(word.tags, ensure_ascii=False),
        "ai_generated": int(word.ai_generated),
        "created_at": _iso_utc(word.created_at),
        "updated_at": _iso_utc(word.updated_at),
        "last_reviewed_at": _iso_utc(word.last_reviewed_at),
        "review_count": word.review_count,
        "ease_factor": word.ease_factor,
        "interval_days": word.interval_days,
        "repetitions": word.repetitions,
        "due_at": _iso_utc(word.due_at),
    }


def _build_filters(
    search: str,
    language: str,
    status: WordStatus | None,
    favorites_only: bool,
    tag: str,
) -> tuple[str, list]:
    """
    Ortak WHERE cümlesini ve parametrelerini kurar.
    get_all ve count aynı filtreleri görsün diye tek yerde tanımlıdır.
    """
    conditions: list[str] = []
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

    where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
    return where_clause, params


INSERT_WORD_SQL = """
INSERT INTO words (
    id, term, language, definition, definition_short,
    synonyms, antonyms, example_sentences, usage_notes,
    part_of_speech, phonetic, audio_url, status, is_favorite, tags, ai_generated,
    created_at, updated_at, last_reviewed_at, review_count,
    ease_factor, interval_days, repetitions, due_at
) VALUES (
    :id, :term, :language, :definition, :definition_short,
    :synonyms, :antonyms, :example_sentences, :usage_notes,
    :part_of_speech, :phonetic, :audio_url, :status, :is_favorite, :tags, :ai_generated,
    :created_at, :updated_at, :last_reviewed_at, :review_count,
    :ease_factor, :interval_days, :repetitions, :due_at
)
"""


class WordRepository:
    """Kelime CRUD operasyonları için repository."""

    def __init__(self, db: Database) -> None:
        self._db = db

    # ── Create ────────────────────────────────────────────────────────────

    def create(self, word: Word) -> Word:
        """Yeni kelime ekler."""
        try:
            with self._db.connection() as conn:
                conn.execute(INSERT_WORD_SQL, _word_to_params(word))
                conn.commit()
            logger.info(f"Kelime eklendi: {word.term} ({word.language})")
            return word
        except Exception as e:
            raise DatabaseError(f"Kelime eklenemedi: {word.term}", original=e) from e

    def create_many(self, words: list[Word]) -> int:
        """
        Birden fazla kelimeyi tek transaction'da ekler. Eklenen sayıyı döndürür.

        Ya hepsi yazılır ya hiçbiri: bir satır hata verirse tamamı geri alınır ve
        veritabanı yarım kalmaz.
        """
        if not words:
            return 0
        try:
            with self._db.transaction() as conn:
                conn.executemany(INSERT_WORD_SQL, [_word_to_params(w) for w in words])
            logger.info(f"{len(words)} kelime toplu eklendi.")
            return len(words)
        except Exception as e:
            raise DatabaseError(
                f"Kelimeler toplu eklenemedi ({len(words)} kayıt)", original=e
            ) from e

    # ── Read ──────────────────────────────────────────────────────────────

    @_wrap_db_errors("Kelime okunamadı")
    def get_by_id(self, word_id: str) -> Word:
        """ID'ye göre kelime getirir."""
        with self._db.connection() as conn:
            row = conn.execute("SELECT * FROM words WHERE id = ?", (word_id,)).fetchone()
        if not row:
            raise WordNotFoundError(word_id)
        return _row_to_word(row)

    @_wrap_db_errors("Kelime listesi okunamadı")
    def get_all(
        self,
        search: str = "",
        language: str = "",
        status: WordStatus | None = None,
        favorites_only: bool = False,
        tag: str = "",
        sort_by: str = "created_at",
        sort_desc: bool = True,
        limit: int = 0,
        offset: int = 0,
    ) -> list[Word]:
        """Filtrelenmiş ve sıralanmış kelime listesi döndürür."""
        where_clause, params = _build_filters(search, language, status, favorites_only, tag)

        # Güvenli sıralama sütunu
        valid_sorts = {"created_at", "updated_at", "term", "review_count"}
        sort_col = sort_by if sort_by in valid_sorts else "created_at"
        order = "DESC" if sort_desc else "ASC"

        sql = f"SELECT * FROM words {where_clause} ORDER BY {sort_col} {order}"

        if limit > 0:
            sql += " LIMIT ?"
            params.append(limit)
            if offset > 0:
                sql += " OFFSET ?"
                params.append(offset)

        with self._db.connection() as conn:
            rows = conn.execute(sql, params).fetchall()

        return [_row_to_word(r) for r in rows]

    @_wrap_db_errors("Kelime varlığı kontrol edilemedi")
    def count(
        self,
        search: str = "",
        language: str = "",
        status: WordStatus | None = None,
        favorites_only: bool = False,
        tag: str = "",
    ) -> int:
        """get_all ile aynı filtrelerle eşleşen toplam kayıt sayısı (sayfalama için)."""
        where_clause, params = _build_filters(search, language, status, favorites_only, tag)
        with self._db.connection() as conn:
            return conn.execute(f"SELECT COUNT(*) FROM words {where_clause}", params).fetchone()[0]

    @_wrap_db_errors("Kelime varlığı kontrol edilemedi")
    def exists(self, term: str, language: str) -> bool:
        """
        Belirtilen kelime ve dil kombinasyonu mevcut mu kontrol eder.

        Karşılaştırma NOCASE'dir: "Run" ile "run" aynı kelime sayılır ve
        idx_words_term (COLLATE NOCASE) indeksiyle örtüşür.
        """
        with self._db.connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM words WHERE term = ? COLLATE NOCASE AND language = ? LIMIT 1",
                (term, language),
            ).fetchone()
        return row is not None

    def get_recent(self, limit: int = 12) -> list[Word]:
        """En son eklenen kelimeleri döndürür."""
        return self.get_all(sort_by="created_at", sort_desc=True, limit=limit)

    @_wrap_db_errors("Son çalışılan kelimeler okunamadı")
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

    @_wrap_db_errors("Çalışma kuyruğu okunamadı")
    def get_due(self, limit: int = 0) -> list[Word]:
        """
        Tekrar zamanı gelmiş kelimeleri döndürür (çalışma kuyruğu).

        Hiç çalışılmamış (due_at IS NULL) kelimeler de kuyruğa dahildir;
        zamanı gelmiş (vadesi geçmiş) kelimeler önce gösterilir.
        """
        now = utcnow().isoformat()
        sql = (
            "SELECT * FROM words WHERE due_at IS NULL OR due_at <= ? "
            "ORDER BY (due_at IS NULL) ASC, due_at ASC"
        )
        params: list = [now]
        if limit > 0:
            sql += " LIMIT ?"
            params.append(limit)
        with self._db.connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_row_to_word(r) for r in rows]

    @_wrap_db_errors("Etiketler okunamadı")
    def get_all_tags(self) -> list[str]:
        """Kullanılan tüm benzersiz etiketleri döndürür."""
        with self._db.connection() as conn:
            rows = conn.execute("SELECT tags FROM words WHERE tags != '[]'").fetchall()
        all_tags: set[str] = set()
        for row in rows:
            tags = json.loads(row["tags"])
            all_tags.update(tags)
        return sorted(all_tags)

    @_wrap_db_errors("Dil dağılımı okunamadı")
    def get_language_counts(self) -> dict[str, int]:
        """
        Dil koduna göre kelime sayısı (kütüphane dil dağılımı).

        Dil algılamada aday sıralamasına hafif önsel olarak kullanılır:
        kullanıcının en çok çalıştığı dil çok dilli kelimede öne alınır.
        idx_words_language indeksiyle örtüşür.
        """
        with self._db.connection() as conn:
            rows = conn.execute(
                "SELECT language, COUNT(*) AS c FROM words GROUP BY language"
            ).fetchall()
        return {row["language"]: row["c"] for row in rows}

    @_wrap_db_errors("İstatistikler okunamadı")
    def get_stats(self) -> WordStats:
        """
        Genel istatistikleri döndürür.

        Tüm sayımlar tek sorguda, koşullu toplamayla alınır: dashboard ve ayarlar
        her açılışta çağırıyordu ve önceki hâl ~10 ayrı COUNT taraması yapıyordu.
        SQLite'ta bir koşul 0/1 döndürür, SUM(koşul) sayımı verir; boş tabloda
        SUM NULL olacağından COALESCE ile 0'a çekilir. NULL bir alan üzerindeki
        koşul (ör. last_reviewed_at) NULL/0 verir, SUM'a katkısı olmaz — bu da
        eski "WHERE ... IS NOT NULL AND ..." COUNT'larıyla aynı sonucu verir.
        """
        day_start, day_end = _local_day_bounds_utc()
        now = utcnow().isoformat()
        with self._db.connection() as conn:
            row = conn.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    COALESCE(SUM(status = 'new'), 0) AS new,
                    COALESCE(SUM(status = 'learning'), 0) AS learning,
                    COALESCE(SUM(status = 'learned'), 0) AS learned,
                    COALESCE(SUM(status = 'needs_review'), 0) AS needs_review,
                    COALESCE(SUM(is_favorite = 1), 0) AS favorites,
                    COALESCE(SUM(created_at >= ? AND created_at < ?), 0) AS added_today,
                    COALESCE(SUM(last_reviewed_at >= ? AND last_reviewed_at < ?), 0)
                        AS reviewed_today,
                    COALESCE(SUM(due_at IS NOT NULL AND due_at <= ?), 0) AS due_today,
                    COALESCE(SUM(due_at IS NULL), 0) AS unreviewed
                FROM words
                """,
                (day_start, day_end, day_start, day_end, now),
            ).fetchone()

        return WordStats(
            total=row["total"],
            new=row["new"],
            learning=row["learning"],
            learned=row["learned"],
            needs_review=row["needs_review"],
            favorites=row["favorites"],
            added_today=row["added_today"],
            reviewed_today=row["reviewed_today"],
            due_today=row["due_today"],
            unreviewed=row["unreviewed"],
        )

    # ── Tekrar geçmişi ────────────────────────────────────────────────────

    @_wrap_db_errors("Tekrar kaydı yazılamadı")
    def log_review(self, word_id: str, grade: int, interval_days: int) -> None:
        """Bir tekrarı geçmişe yazar (streak ve aktivite grafiği için)."""
        with self._db.connection() as conn:
            conn.execute(
                "INSERT INTO review_log (id, word_id, grade, reviewed_at, interval_days) "
                "VALUES (?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), word_id, int(grade), utcnow().isoformat(), interval_days),
            )
            conn.commit()

    @_wrap_db_errors("Tekrar geçmişi okunamadı")
    def get_review_counts(self, days: int = 7) -> dict[date, int]:
        """
        Son `days` gün için gün başına tekrar sayısı (yerel güne göre).

        Hiç tekrar yapılmayan günler 0 ile doldurulur; grafik boşluksuz çizilsin.
        """
        today = datetime.now().astimezone().date()
        counts: dict[date, int] = {
            today - timedelta(days=offset): 0 for offset in range(days - 1, -1, -1)
        }

        oldest = today - timedelta(days=days - 1)
        start_utc = (
            datetime.combine(oldest, dtime.min).astimezone().astimezone(timezone.utc).isoformat()
        )

        with self._db.connection() as conn:
            rows = conn.execute(
                "SELECT reviewed_at FROM review_log WHERE reviewed_at >= ?",
                (start_utc,),
            ).fetchall()

        for row in rows:
            # UTC saklanır, kullanıcının yerel gününe düşürülür.
            local_day = datetime.fromisoformat(row["reviewed_at"]).astimezone().date()
            if local_day in counts:
                counts[local_day] += 1

        return counts

    @_wrap_db_errors("Seri (streak) hesaplanamadı")
    def get_streak(self) -> int:
        """
        Kesintisiz çalışılan gün sayısı (yerel güne göre).

        Bugün henüz çalışılmadıysa seri bozulmuş sayılmaz: dün çalışıldıysa seri
        dünden geriye doğru sayılır.
        """
        with self._db.connection() as conn:
            rows = conn.execute(
                "SELECT DISTINCT reviewed_at FROM review_log ORDER BY reviewed_at DESC"
            ).fetchall()

        if not rows:
            return 0

        days = {datetime.fromisoformat(r["reviewed_at"]).astimezone().date() for r in rows}
        today = datetime.now().astimezone().date()

        if today in days:
            cursor = today
        elif (today - timedelta(days=1)) in days:
            cursor = today - timedelta(days=1)
        else:
            return 0

        streak = 0
        while cursor in days:
            streak += 1
            cursor -= timedelta(days=1)
        return streak

    # ── Update ────────────────────────────────────────────────────────────

    def update(self, word: Word) -> Word:
        """Mevcut kelimeyi günceller."""
        word.updated_at = utcnow()
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
                        review_count = :review_count,
                        ease_factor = :ease_factor,
                        interval_days = :interval_days,
                        repetitions = :repetitions,
                        due_at = :due_at
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

    @_wrap_db_errors("Kelime silinemedi")
    def delete(self, word_id: str) -> None:
        """
        Kelimeyi siler.

        Raises:
            WordNotFoundError: Verilen id'de kelime yoksa.
        """
        with self._db.connection() as conn:
            cursor = conn.execute("DELETE FROM words WHERE id = ?", (word_id,))
            if cursor.rowcount == 0:
                raise WordNotFoundError(word_id)
            conn.commit()
        logger.info(f"Kelime silindi: {word_id}")

    @_wrap_db_errors("Kelimeler silinemedi")
    def delete_all(self) -> int:
        """Tüm kelimeleri siler. Silinen sayısını döndürür."""
        with self._db.connection() as conn:
            count = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
            conn.execute("DELETE FROM words")
            conn.commit()
        return count
