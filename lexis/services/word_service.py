"""
Lexis — Word Service

Kelime yönetimi için uygulama/iş mantığı katmanı.
Repository ve AI servisini koordine eder.
"""

from __future__ import annotations

import logging
from typing import Optional

from lexis.domain.exceptions import DuplicateWordError
from lexis.domain.models import Word, WordStats, WordStatus
from lexis.persistence.word_repository import WordRepository
from lexis.services.ai_service import AIService

logger = logging.getLogger(__name__)


class WordService:
    """Kelime ekleme, güncelleme ve sorgulama iş mantığı."""

    def __init__(self, repository: WordRepository, ai_service: AIService) -> None:
        self._repo = repository
        self._ai = ai_service

    # ── Sorgulama ─────────────────────────────────────────────────────────

    def get_all(
        self,
        search: str = "",
        language: str = "",
        status: Optional[WordStatus] = None,
        favorites_only: bool = False,
        tag: str = "",
        sort_by: str = "created_at",
        sort_desc: bool = True,
    ) -> list[Word]:
        return self._repo.get_all(
            search=search,
            language=language,
            status=status,
            favorites_only=favorites_only,
            tag=tag,
            sort_by=sort_by,
            sort_desc=sort_desc,
        )

    def get_by_id(self, word_id: str) -> Word:
        return self._repo.get_by_id(word_id)

    def get_recent(self, limit: int = 12) -> list[Word]:
        return self._repo.get_recent(limit=limit)

    def get_recently_reviewed(self, limit: int = 6) -> list[Word]:
        return self._repo.get_recently_reviewed(limit=limit)

    def get_stats(self) -> WordStats:
        return self._repo.get_stats()

    def get_all_tags(self) -> list[str]:
        return self._repo.get_all_tags()

    # ── Ekleme & Güncelleme ───────────────────────────────────────────────

    def add_word(
        self,
        term: str,
        language: str = "en",
        ai_data: Optional[dict] = None,
    ) -> Word:
        """
        Yeni kelime ekler.

        Args:
            term: Eklenecek kelime.
            language: Kelime dili ('en', 'de', vb.)
            ai_data: Önceden üretilmiş AI verisi. None ise boş Word oluşturulur.

        Raises:
            DuplicateWordError: Aynı kelime zaten mevcutsa.
        """
        term = term.strip()
        if self._repo.exists(term, language):
            raise DuplicateWordError(term, language)

        word = Word(term=term, language=language)

        if ai_data:
            word.definition = ai_data.get("definition", "")
            word.definition_short = ai_data.get("definition_short", "")
            word.part_of_speech = ai_data.get("part_of_speech", "")
            word.synonyms = ai_data.get("synonyms", [])
            word.antonyms = ai_data.get("antonyms", [])
            word.example_sentences = ai_data.get("example_sentences", [])
            word.usage_notes = ai_data.get("usage_notes", "")
            word.ai_generated = True

        return self._repo.create(word)

    def update_word(self, word: Word) -> Word:
        """Mevcut kelimeyi günceller."""
        return self._repo.update(word)

    def delete_word(self, word_id: str) -> None:
        """Kelimeyi siler."""
        self._repo.delete(word_id)

    def toggle_favorite(self, word_id: str) -> Word:
        """Favorilere ekler/çıkarır."""
        word = self._repo.get_by_id(word_id)
        word.is_favorite = not word.is_favorite
        return self._repo.update(word)

    def update_status(self, word_id: str, status: WordStatus) -> Word:
        """Kelime öğrenme durumunu günceller."""
        word = self._repo.get_by_id(word_id)
        word.status = status
        word.mark_reviewed()
        return self._repo.update(word)

    def add_tag(self, word_id: str, tag: str) -> Word:
        """Kelimeye etiket ekler."""
        word = self._repo.get_by_id(word_id)
        tag = tag.strip().lower()
        if tag and tag not in word.tags:
            word.tags.append(tag)
            self._repo.update(word)
        return word

    def remove_tag(self, word_id: str, tag: str) -> Word:
        """Kelimeden etiket kaldırır."""
        word = self._repo.get_by_id(word_id)
        if tag in word.tags:
            word.tags.remove(tag)
            self._repo.update(word)
        return word

    def mark_reviewed(self, word_id: str) -> Word:
        """Kelimeyi çalışıldı olarak işaretler."""
        word = self._repo.get_by_id(word_id)
        word.mark_reviewed()
        return self._repo.update(word)

    # ── AI Üretim ─────────────────────────────────────────────────────────

    def generate_ai_content(self, term: str, language: str = "en") -> dict:
        """
        AI ile kelime içeriği üretir.
        Bu metot doğrudan çağrılırsa UI'ı bloklar;
        QThread worker üzerinden çağrılması önerilir.
        """
        return self._ai.generate_word_data(term, language)

    def regenerate_ai_content(self, word_id: str) -> Word:
        """Mevcut kelimenin AI içeriğini yeniler."""
        word = self._repo.get_by_id(word_id)
        ai_data = self._ai.generate_word_data(word.term, word.language)
        word.definition = ai_data.get("definition", word.definition)
        word.definition_short = ai_data.get("definition_short", word.definition_short)
        word.part_of_speech = ai_data.get("part_of_speech", word.part_of_speech)
        word.synonyms = ai_data.get("synonyms", word.synonyms)
        word.antonyms = ai_data.get("antonyms", word.antonyms)
        word.example_sentences = ai_data.get("example_sentences", word.example_sentences)
        word.usage_notes = ai_data.get("usage_notes", word.usage_notes)
        word.ai_generated = True
        return self._repo.update(word)

    @property
    def ai_configured(self) -> bool:
        return self._ai.is_configured
