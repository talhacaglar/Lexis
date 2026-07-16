"""
Lexis — Tests: Word Service
"""

import pytest

from lexis.domain.exceptions import DuplicateWordError
from lexis.domain.models import WordStatus
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


class TestContentProviderSelection:
    """Anahtar yoksa açık sözlüğe, varsa Gemini'ye gitmeli."""

    def test_uses_open_dictionary_without_api_key(self, repo, ai_service):
        fake = _RecordingProvider()
        service = WordService(repo, ai_service, open_dictionary=fake)

        assert service.ai_configured is False
        assert service.content_source == "Açık sözlük"

        data = service.generate_content("ephemeral", "en")

        assert fake.calls == [("ephemeral", "en")]
        assert data["definition"] == "sahte tanım"

    def test_uses_gemini_when_configured(self, repo, ai_service, monkeypatch):
        fake_open = _RecordingProvider()
        service = WordService(repo, ai_service, open_dictionary=fake_open)

        monkeypatch.setattr(type(ai_service), "is_configured", property(lambda _: True))
        monkeypatch.setattr(
            ai_service, "generate_word_data", lambda t, lang: {"definition": "gemini tanımı"}
        )

        assert service.content_source == "Gemini"
        data = service.generate_content("ephemeral", "en")

        assert data["definition"] == "gemini tanımı"
        assert fake_open.calls == []  # açık sözlüğe hiç gidilmemeli

    def test_add_word_stores_pronunciation(self, repo, ai_service):
        service = WordService(repo, ai_service, open_dictionary=_RecordingProvider())
        data = service.generate_content("ephemeral", "en")

        word = service.add_word("ephemeral", "en", ai_data=data)

        saved = service.get_by_id(word.id)
        assert saved.phonetic == "/təst/"
        assert saved.audio_url == "https://example.org/a.mp3"


class TestApplyContent:
    def test_missing_fields_keep_existing_values(self, word_service: WordService):
        """Açık sözlük bazı alanları boş bırakabilir; mevcut içeriği silmemeli."""
        word = word_service.add_word("ephemeral", "en", ai_data={
            "definition": "eski tanım",
            "usage_notes": "eski not",
            "synonyms": ["a", "b"],
        })

        word_service.apply_content(word, {"definition": "yeni tanım", "usage_notes": ""})

        assert word.definition == "yeni tanım"
        assert word.usage_notes == "eski not"
        assert word.synonyms == ["a", "b"]


class _RecordingProvider:
    """Ağa çıkmayan sahte sağlayıcı; hangi çağrıların yapıldığını kaydeder."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    @property
    def is_configured(self) -> bool:
        return True

    def generate_word_data(self, term: str, language: str = "en") -> dict:
        self.calls.append((term, language))
        return {
            "definition": "sahte tanım",
            "definition_short": "sahte",
            "part_of_speech": "noun",
            "synonyms": [],
            "antonyms": [],
            "example_sentences": [],
            "usage_notes": "",
            "phonetic": "/təst/",
            "audio_url": "https://example.org/a.mp3",
        }
