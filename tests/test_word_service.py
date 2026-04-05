"""
Lexis — Tests: Word Service
"""

import pytest
from lexis.domain.exceptions import DuplicateWordError
from lexis.domain.models import Word, WordStatus
from lexis.services.word_service import WordService


class TestWordServiceAdd:
    def test_add_word_creates_entry(self, word_service: WordService):
        word = word_service.add_word("ephemeral", "en")
        assert word.term == "ephemeral"
        assert word.language == "en"
        assert word.status == WordStatus.NEW

    def test_add_word_with_ai_data(self, word_service: WordService):
        ai_data = {
            "definition": "Lasting for a very short time.",
            "definition_short": "Kısa süreli.",
            "synonyms": ["transient"],
            "antonyms": ["permanent"],
            "example_sentences": ["Fame can be ephemeral."],
            "usage_notes": "Kısa süreli şeyler için.",
            "part_of_speech": "Sıfat",
        }
        word = word_service.add_word("ephemeral", "en", ai_data=ai_data)
        assert word.definition == "Lasting for a very short time."
        assert word.synonyms == ["transient"]
        assert word.ai_generated is True

    def test_add_duplicate_raises(self, word_service: WordService):
        word_service.add_word("ephemeral", "en")
        with pytest.raises(DuplicateWordError):
            word_service.add_word("ephemeral", "en")

    def test_add_same_term_different_language_ok(self, word_service: WordService):
        word_service.add_word("ephemeral", "en")
        word2 = word_service.add_word("ephemeral", "de")
        assert word2.language == "de"


class TestWordServiceOperations:
    def test_toggle_favorite(self, word_service: WordService):
        word = word_service.add_word("serendipity", "en")
        assert word.is_favorite is False
        word = word_service.toggle_favorite(word.id)
        assert word.is_favorite is True
        word = word_service.toggle_favorite(word.id)
        assert word.is_favorite is False

    def test_update_status(self, word_service: WordService):
        word = word_service.add_word("ubiquitous", "en")
        updated = word_service.update_status(word.id, WordStatus.LEARNED)
        assert updated.status == WordStatus.LEARNED
        assert updated.review_count == 1

    def test_add_and_remove_tag(self, word_service: WordService):
        word = word_service.add_word("nostalgia", "en")
        word = word_service.add_tag(word.id, "emotion")
        assert "emotion" in word.tags

        word = word_service.remove_tag(word.id, "emotion")
        assert "emotion" not in word.tags

    def test_add_duplicate_tag_ignored(self, word_service: WordService):
        word = word_service.add_word("melancholy", "en")
        word_service.add_tag(word.id, "emotion")
        word = word_service.add_tag(word.id, "emotion")
        assert word.tags.count("emotion") == 1

    def test_mark_reviewed_increments_count(self, word_service: WordService):
        word = word_service.add_word("resilience", "en")
        word = word_service.mark_reviewed(word.id)
        assert word.review_count == 1
        word = word_service.mark_reviewed(word.id)
        assert word.review_count == 2

    def test_get_stats_reflects_changes(self, word_service: WordService):
        word = word_service.add_word("equanimity", "en")
        word_service.update_status(word.id, WordStatus.LEARNED)
        stats = word_service.get_stats()
        assert stats.learned == 1
        assert stats.total >= 1

    def test_delete_word(self, word_service: WordService):
        word = word_service.add_word("transient", "en")
        word_service.delete_word(word.id)
        results = word_service.get_all()
        assert all(w.id != word.id for w in results)
