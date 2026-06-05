"""
Lexis — Tests: Aralıklı tekrar (SM-2) ve migration
"""

import sqlite3

from lexis.domain.models import ReviewGrade, Word, WordStatus, compute_sm2, utcnow
from lexis.persistence.database import Database
from lexis.persistence.word_repository import WordRepository
from lexis.services.word_service import WordService

# ── SM-2 saf fonksiyon ────────────────────────────────────────────────────

def test_sm2_first_good_review_sets_interval_1():
    ease, interval, reps = compute_sm2(2.5, 0, 0, ReviewGrade.GOOD)
    assert interval == 1
    assert reps == 1
    assert ease >= 2.5


def test_sm2_second_good_review_sets_interval_6():
    ease, interval, reps = compute_sm2(2.5, 1, 1, ReviewGrade.GOOD)
    assert interval == 6
    assert reps == 2


def test_sm2_third_review_multiplies_by_ease():
    ease, interval, reps = compute_sm2(2.5, 6, 2, ReviewGrade.GOOD)
    assert interval == round(6 * 2.5)
    assert reps == 3


def test_sm2_again_resets_progress():
    ease, interval, reps = compute_sm2(2.5, 30, 5, ReviewGrade.AGAIN)
    assert reps == 0
    assert interval == 1


def test_sm2_ease_never_below_1_3():
    ease = 1.3
    for _ in range(10):
        ease, _i, _r = compute_sm2(ease, 1, 0, ReviewGrade.AGAIN)
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


def test_stats_due_today(word_service: WordService):
    word_service.add_word("nascent", "en")
    stats = word_service.get_stats()
    assert stats.due_today >= 1


# ── v1 → v2 migration ─────────────────────────────────────────────────────

def test_migration_adds_sr_columns(tmp_path):
    """Eski (v1) şemalı bir DB açıldığında yeni sütunlar eklenmeli."""
    db_file = tmp_path / "old.db"
    conn = sqlite3.connect(str(db_file))
    conn.execute(
        """
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
    )
    now = utcnow().isoformat()
    conn.execute(
        "INSERT INTO words (id, term, created_at, updated_at) VALUES (?, ?, ?, ?)",
        ("w1", "legacy", now, now),
    )
    conn.commit()
    conn.close()

    # Database açılışı migration uygular
    db = Database(db_file)
    repo = WordRepository(db)
    word = repo.get_by_id("w1")
    assert word.ease_factor == 2.5
    assert word.repetitions == 0
    assert word.due_at is None
