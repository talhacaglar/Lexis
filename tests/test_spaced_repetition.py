"""
Lexis — Tests: Aralıklı tekrar (SM-2) ve migration
"""

import sqlite3
from datetime import datetime, timedelta

from lexis.domain.models import (
    HARD_INTERVAL_FACTOR,
    LEARNED_INTERVAL_DAYS,
    RELEARN_DELAY_MINUTES,
    ReviewGrade,
    Word,
    WordStatus,
    compute_sm2,
    utcnow,
)
from lexis.persistence.database import SCHEMA_VERSION, Database
from lexis.persistence.word_repository import WordRepository
from lexis.services.word_service import WordService

# ── SM-2 saf fonksiyon ────────────────────────────────────────────────────


def test_sm2_first_good_review_sets_interval_1():
    ease, interval, reps, delay = compute_sm2(2.5, 0, 0, ReviewGrade.GOOD)
    assert interval == 1
    assert reps == 1
    assert ease >= 2.5
    assert delay == 0


def test_sm2_second_good_review_sets_interval_6():
    _ease, interval, reps, _delay = compute_sm2(2.5, 1, 1, ReviewGrade.GOOD)
    assert interval == 6
    assert reps == 2


def test_sm2_third_review_multiplies_by_ease():
    _ease, interval, reps, _delay = compute_sm2(2.5, 6, 2, ReviewGrade.GOOD)
    assert interval == round(6 * 2.5)
    assert reps == 3


def test_sm2_again_reschedules_within_session():
    """Hatırlanamayan kart bir gün sonrasına değil, dakikalar sonrasına planlanır."""
    _ease, interval, reps, delay = compute_sm2(2.5, 30, 5, ReviewGrade.AGAIN)
    assert reps == 0
    assert interval == 0
    assert delay == RELEARN_DELAY_MINUTES


def test_sm2_hard_grows_slower_than_good():
    """'Zor', 'İyi'den belirgin biçimde kısa bir aralık vermeli."""
    _e, hard_interval, _r, _d = compute_sm2(2.5, 10, 3, ReviewGrade.HARD)
    _e2, good_interval, _r2, _d2 = compute_sm2(2.5, 10, 3, ReviewGrade.GOOD)

    assert hard_interval == round(10 * HARD_INTERVAL_FACTOR)  # 12
    assert good_interval == round(10 * 2.5)  # 25
    assert hard_interval < good_interval


def test_sm2_hard_still_uses_ladder_for_early_reviews():
    """İlk iki tekrarda 1/6 günlük merdiven korunur."""
    _e, interval, _r, _d = compute_sm2(2.5, 0, 0, ReviewGrade.HARD)
    assert interval == 1


def test_sm2_ease_never_below_1_3():
    ease = 1.3
    for _ in range(10):
        ease, _i, _r, _d = compute_sm2(ease, 1, 0, ReviewGrade.AGAIN)
    assert ease >= 1.3


# ── Word.apply_review ─────────────────────────────────────────────────────


def test_apply_review_schedules_due_date():
    word = Word(term="ephemeral")
    assert word.is_due is True  # yeni kelime daima due
    word.apply_review(ReviewGrade.GOOD)
    assert word.due_at is not None
    assert word.due_at > utcnow()
    assert word.is_due is False
    assert word.review_count == 1


def test_apply_review_again_marks_needs_review():
    word = Word(term="serendipity")
    word.apply_review(ReviewGrade.AGAIN)
    assert word.status == WordStatus.NEEDS_REVIEW


def test_apply_review_again_schedules_minutes_not_days():
    """'Tekrar' verilen kart aynı oturumda geri gelebilmeli."""
    word = Word(term="serendipity", interval_days=30, repetitions=5)
    word.apply_review(ReviewGrade.AGAIN)

    assert word.due_at is not None
    delta = word.due_at - utcnow()
    assert timedelta(minutes=5) < delta <= timedelta(minutes=RELEARN_DELAY_MINUTES)


def test_word_becomes_learned_once_interval_matures():
    word = Word(term="diligent")
    for _ in range(4):
        word.apply_review(ReviewGrade.GOOD)

    assert word.repetitions == 4
    assert word.interval_days >= LEARNED_INTERVAL_DAYS
    assert word.status == WordStatus.LEARNED


def test_hard_review_does_not_permanently_block_learned():
    """
    Tek bir 'Zor' ease'i 2.5'in altına düşürür; eski kapı bu durumda LEARNED'ı
    kilitliyordu. Aralık olgunlaştığında durum yine LEARNED olmalı.
    """
    word = Word(term="stubborn")
    word.apply_review(ReviewGrade.HARD)
    assert word.ease_factor < 2.5

    for _ in range(6):
        word.apply_review(ReviewGrade.GOOD)

    assert word.interval_days >= LEARNED_INTERVAL_DAYS
    assert word.status == WordStatus.LEARNED


# ── Service + repository akışı ────────────────────────────────────────────


def test_review_word_flow(word_service: WordService):
    word = word_service.add_word("ubiquitous", "en")
    # Yeni kelime due kuyruğunda olmalı
    due = word_service.get_due_words()
    assert any(w.id == word.id for w in due)

    reviewed = word_service.review_word(word.id, ReviewGrade.GOOD)
    assert reviewed.due_at is not None

    # Çalışıldıktan sonra (gelecekte due) kuyruktan çıkmalı
    due_after = word_service.get_due_words()
    assert all(w.id != word.id for w in due_after)


def test_stats_separates_unreviewed_from_scheduled(word_service: WordService):
    """
    Yeni eklenen kelime 'due_today' değil 'unreviewed' sayılır; due_today
    yalnızca planlanmış (daha önce çalışılmış) tekrarları gösterir.
    """
    word = word_service.add_word("nascent", "en")

    stats = word_service.get_stats()
    assert stats.unreviewed == 1
    assert stats.due_today == 0
    assert stats.practice_queue_size == 1

    # Çalışıldıktan sonra ileri bir tarihe planlanır: artık ikisinde de sayılmaz.
    word_service.review_word(word.id, ReviewGrade.GOOD)
    stats_after = word_service.get_stats()
    assert stats_after.unreviewed == 0
    assert stats_after.due_today == 0


def test_stats_due_today_counts_overdue_scheduled_word(word_service: WordService):
    """Vadesi geçmiş planlı bir tekrar due_today'e girer."""
    word = word_service.add_word("overdue", "en")
    word.due_at = utcnow() - timedelta(days=1)
    word.interval_days = 3
    word_service.update_word(word)

    stats = word_service.get_stats()
    assert stats.due_today == 1
    assert stats.unreviewed == 0


# ── Migration zinciri ─────────────────────────────────────────────────────

# SM-2 sütunları eklenmeden önceki (v1) words şeması.
V1_WORDS_SCHEMA = """
CREATE TABLE words (
    id TEXT PRIMARY KEY, term TEXT NOT NULL, language TEXT DEFAULT 'en',
    definition TEXT DEFAULT '', definition_short TEXT DEFAULT '',
    synonyms TEXT DEFAULT '[]', antonyms TEXT DEFAULT '[]',
    example_sentences TEXT DEFAULT '[]', usage_notes TEXT DEFAULT '',
    part_of_speech TEXT DEFAULT '', status TEXT DEFAULT 'new',
    is_favorite INTEGER DEFAULT 0, tags TEXT DEFAULT '[]',
    ai_generated INTEGER DEFAULT 1, created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL, last_reviewed_at TEXT, review_count INTEGER DEFAULT 0
)
"""


def _make_v1_db(db_file, term: str = "legacy") -> None:
    """Verilen yola v1 şemalı, tek kayıtlı bir veritabanı yazar."""
    conn = sqlite3.connect(str(db_file))
    conn.execute(V1_WORDS_SCHEMA)
    now = utcnow().isoformat()
    conn.execute(
        "INSERT INTO words (id, term, created_at, updated_at) VALUES (?, ?, ?, ?)",
        ("w1", term, now, now),
    )
    conn.commit()
    conn.close()


def test_migration_adds_sr_columns(tmp_path):
    """Eski (v1) şemalı bir DB açıldığında yeni sütunlar eklenmeli."""
    db_file = tmp_path / "old.db"
    _make_v1_db(db_file)

    # Database açılışı migration uygular
    db = Database(db_file)
    repo = WordRepository(db)
    word = repo.get_by_id("w1")
    assert word.ease_factor == 2.5
    assert word.repetitions == 0
    assert word.due_at is None


def test_migration_v1_db_reaches_current_version(tmp_path):
    """v1 şemalı DB zincirin tamamından geçip güncel sürüme ulaşmalı, veri korunmalı."""
    db_file = tmp_path / "old.db"
    _make_v1_db(db_file, term="korunacak")

    db = Database(db_file)

    assert WordRepository(db).get_by_id("w1").term == "korunacak"

    with db.connection() as c:
        version = c.execute("SELECT version FROM schema_version").fetchone()["version"]
        tables = {r["name"] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    assert version == SCHEMA_VERSION
    assert "review_log" in tables


def test_migration_v2_to_v3_adds_review_log(tmp_path):
    """v2 (review_log'suz) bir DB açıldığında tablo eklenmeli, veri korunmalı."""
    db_file = tmp_path / "v2.db"
    db = Database(db_file)
    repo = WordRepository(db)
    repo.create(Word(term="kalici", language="en"))

    # v2'ye geri sar: review_log'u düşür, sürümü 2 yap.
    with db.connection() as c:
        c.execute("DROP TABLE review_log")
        c.execute("DELETE FROM schema_version")
        c.execute("INSERT INTO schema_version (version) VALUES (2)")
        c.commit()

    reopened = Database(db_file)

    with reopened.connection() as c:
        version = c.execute("SELECT version FROM schema_version").fetchone()["version"]
        tables = {r["name"] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    assert version == SCHEMA_VERSION
    assert "review_log" in tables
    assert WordRepository(reopened).get_all()[0].term == "kalici"


def test_migration_v3_to_v4_adds_pronunciation_columns(tmp_path):
    """v3 (telaffuzsuz) bir DB açıldığında sütunlar eklenmeli, veri korunmalı."""
    db_file = tmp_path / "v3.db"
    db = Database(db_file)
    repo = WordRepository(db)
    repo.create(Word(term="korunacak", language="en", definition="tanım"))

    # v3'e geri sar: telaffuz sütunlarını düşür, sürümü 3 yap.
    with db.connection() as c:
        c.execute("ALTER TABLE words DROP COLUMN phonetic")
        c.execute("ALTER TABLE words DROP COLUMN audio_url")
        c.execute("DELETE FROM schema_version")
        c.execute("INSERT INTO schema_version (version) VALUES (3)")
        c.commit()

    reopened = WordRepository(Database(db_file))
    word = reopened.get_all()[0]

    assert word.term == "korunacak"
    assert word.definition == "tanım"
    assert word.phonetic == ""  # yeni sütun varsayılanla geldi
    assert word.audio_url == ""


def test_pronunciation_round_trips(repo: WordRepository):
    repo.create(
        Word(term="ephemeral", language="en", phonetic="/əˈfɛmərəl/", audio_url="https://x/a.mp3")
    )
    saved = repo.get_all()[0]
    assert saved.phonetic == "/əˈfɛmərəl/"
    assert saved.audio_url == "https://x/a.mp3"


def test_migrations_are_idempotent_on_reopen(tmp_path):
    """Güncel bir DB tekrar tekrar açıldığında veri bozulmamalı."""
    db_file = tmp_path / "current.db"
    repo = WordRepository(Database(db_file))
    repo.create(Word(term="tekrar", language="en"))

    for _ in range(3):
        repo = WordRepository(Database(db_file))

    assert len(repo.get_all()) == 1


# ── Tekrar geçmişi (review_log) ───────────────────────────────────────────


def test_review_word_writes_history(word_service: WordService):
    word = word_service.add_word("history", "en")
    word_service.review_word(word.id, ReviewGrade.GOOD)
    word_service.review_word(word.id, ReviewGrade.HARD)

    counts = word_service.get_review_counts(days=7)
    today = datetime.now().astimezone().date()
    assert counts[today] == 2


def test_review_counts_fills_empty_days(word_service: WordService):
    counts = word_service.get_review_counts(days=7)
    assert len(counts) == 7
    assert set(counts.values()) == {0}


def test_deleting_word_removes_its_history(word_service: WordService, repo: WordRepository):
    """review_log word_id'ye ON DELETE CASCADE ile bağlı."""
    word = word_service.add_word("gecici", "en")
    word_service.review_word(word.id, ReviewGrade.GOOD)
    word_service.delete_word(word.id)

    today = datetime.now().astimezone().date()
    assert repo.get_review_counts(days=7)[today] == 0


def test_streak_is_zero_without_reviews(repo: WordRepository):
    assert repo.get_streak() == 0


def test_streak_counts_today(word_service: WordService):
    word = word_service.add_word("bugun", "en")
    word_service.review_word(word.id, ReviewGrade.GOOD)
    assert word_service.get_streak() == 1


def test_streak_counts_consecutive_days(word_service: WordService, repo: WordRepository, tmp_db):
    """Ardışık günlerde çalışılmışsa seri o günleri saymalı."""
    word = word_service.add_word("seri", "en")
    now = utcnow()

    with tmp_db.connection() as conn:
        for offset in range(3):  # bugün, dün, evvelsi gün
            conn.execute(
                "INSERT INTO review_log (id, word_id, grade, reviewed_at, interval_days) "
                "VALUES (?, ?, ?, ?, ?)",
                (f"r{offset}", word.id, 4, (now - timedelta(days=offset)).isoformat(), 1),
            )
        conn.commit()

    assert repo.get_streak() == 3


def test_streak_breaks_on_gap(word_service: WordService, repo: WordRepository, tmp_db):
    """Aradaki boş gün seriyi kesmeli."""
    word = word_service.add_word("bosluk", "en")
    now = utcnow()

    with tmp_db.connection() as conn:
        for offset in (0, 3, 4):  # bugün, sonra 3 gün önce (arada boşluk)
            conn.execute(
                "INSERT INTO review_log (id, word_id, grade, reviewed_at, interval_days) "
                "VALUES (?, ?, ?, ?, ?)",
                (f"r{offset}", word.id, 4, (now - timedelta(days=offset)).isoformat(), 1),
            )
        conn.commit()

    assert repo.get_streak() == 1


def test_streak_survives_today_without_review(
    word_service: WordService, repo: WordRepository, tmp_db
):
    """Bugün henüz çalışılmadıysa dünkü seri hâlâ ayakta sayılır."""
    word = word_service.add_word("dun", "en")
    now = utcnow()

    with tmp_db.connection() as conn:
        for offset in (1, 2):  # dün ve evvelsi gün
            conn.execute(
                "INSERT INTO review_log (id, word_id, grade, reviewed_at, interval_days) "
                "VALUES (?, ?, ?, ?, ?)",
                (f"r{offset}", word.id, 4, (now - timedelta(days=offset)).isoformat(), 1),
            )
        conn.commit()

    assert repo.get_streak() == 2
