"""
Lexis — Tests: Word Service
"""

import pytest

from lexis.domain.exceptions import ContentProviderError, DuplicateWordError
from lexis.domain.models import Word, WordStatus
from lexis.services.word_service import MAX_AI_LANGUAGE_ATTEMPTS, WordService


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

    def test_auto_tries_the_next_language_when_the_word_is_not_found(self, repo, ai_service):
        """
        Çok dilli kelimede ilk tahminde pes edilmemeli.

        Gerçek vaka: "Baran" İngilizce'de sözlük kelimesi değil ama Lehçe'de
        "koç" demek. Wiktionary ikisini de aday gösteriyor; İngilizce denenip
        vazgeçilince kullanıcı haksız yere "bulunamadı" görüyordu.
        """
        provider = _LanguageAwareProvider(known={"pl": "koç"})
        service = WordService(repo, ai_service, open_dictionary=provider)
        provider.candidates = ["en", "pl"]

        data, language = service.generate_auto("Baran")

        assert language == "pl"
        assert data["definition"] == "koç"
        assert provider.calls == [("Baran", "en"), ("Baran", "pl")]

    def test_auto_stops_at_the_first_language_that_works(self, repo, ai_service):
        """Tutan adaydan sonrası denenmemeli: her deneme bir ağ isteği."""
        provider = _LanguageAwareProvider(known={"en": "ram"})
        service = WordService(repo, ai_service, open_dictionary=provider)
        provider.candidates = ["en", "pl", "de"]

        _data, language = service.generate_auto("ram")

        assert language == "en"
        assert provider.calls == [("ram", "en")]

    def test_auto_raises_when_no_language_has_the_word(self, repo, ai_service):
        provider = _LanguageAwareProvider(known={})
        service = WordService(repo, ai_service, open_dictionary=provider)
        provider.candidates = ["en", "pl"]

        with pytest.raises(ContentProviderError):
            service.generate_auto("zzzqqxyz")

    def test_auto_error_names_every_tried_language(self, repo, ai_service):
        """
        Hata mesajı yalnızca son adayın dilini değil, denenen tüm dilleri saymalı.

        "İngilizce'de yok" mesajı diğer dillerin hiç denenmediği izlenimini
        veriyordu; kullanıcı da haklı olarak "Almanca olabilir mi? Rusça
        olabilir mi?" diye soruyordu.
        """
        provider = _LanguageAwareProvider(known={})
        service = WordService(repo, ai_service, open_dictionary=provider)
        provider.candidates = ["en", "pl"]

        with pytest.raises(ContentProviderError) as exc:
            service.generate_auto("Baran")

        assert "İngilizce" in str(exc.value)
        assert "Lehçe" in str(exc.value)

    def test_auto_tries_every_candidate_without_gemini(self, repo, ai_service):
        """
        Anahtarsız modda adaylar kesilmez ("her dil için sorgulasın").

        Açık sözlükte ek aday ek ağ maliyeti getirmiyor: Wiktionary sayfası
        önbellekten paylaşılıyor.
        """
        provider = _LanguageAwareProvider(known={"sv": "tak"})
        service = WordService(repo, ai_service, open_dictionary=provider)
        provider.candidates = ["en", "de", "fr", "es", "sv"]

        _data, language = service.generate_auto("tak")

        assert language == "sv"
        assert len(provider.calls) == 5

    def test_auto_caps_attempts_when_gemini_is_configured(self, repo, ai_service, monkeypatch):
        """
        Gemini'de her aday ayrı bir ücretli istek (birkaç saniye); sınırsız
        aday, bulunamayan kelimede kullanıcıyı dakikalarca bekletir ve kotayı
        tüketirdi.
        """
        provider = _LanguageAwareProvider(known={})
        service = WordService(repo, ai_service, open_dictionary=provider)
        provider.candidates = ["en", "de", "fr", "es", "it"]

        monkeypatch.setattr(type(ai_service), "is_configured", property(lambda _: True))
        ai_calls: list[str] = []

        def ai_not_found(term, language):
            ai_calls.append(language)
            raise ContentProviderError(f"'{term}' {language} dilinde yok.")

        monkeypatch.setattr(ai_service, "generate_word_data", ai_not_found)

        with pytest.raises(ContentProviderError):
            service.generate_auto("Baran")

        assert ai_calls == provider.candidates[:MAX_AI_LANGUAGE_ATTEMPTS]

    def test_auto_does_not_retry_other_languages_on_a_real_failure(self, repo, ai_service):
        """
        Ağ/anahtar arızasında adaylar taranmamalı.

        Taransaydı çökmüş bir servis için kullanıcı aynı hatayı üç kez beklerdi.
        """
        provider = _LanguageAwareProvider(known={})
        provider.explode = RuntimeError("ağ yok")
        service = WordService(repo, ai_service, open_dictionary=provider)
        provider.candidates = ["en", "pl", "de"]

        with pytest.raises(RuntimeError):
            service.generate_auto("ephemeral")

        assert len(provider.calls) == 1

    def test_add_word_stores_pronunciation(self, repo, ai_service):
        service = WordService(repo, ai_service, open_dictionary=_RecordingProvider())
        data = service.generate_content("ephemeral", "en")

        word = service.add_word("ephemeral", "en", ai_data=data)

        saved = service.get_by_id(word.id)
        assert saved.phonetic == "/təst/"
        assert saved.audio_url == "https://example.org/a.mp3"


class TestLibraryLanguagePrior:
    """
    Çok dilli kelimede kullanıcının en çok çalıştığı dil öne alınır.

    İngilizce baştaysa yerinde kalır: telaffuz/ses veren tek zengin kaynağa
    bağlı olma avantajı bozulmamalı.
    """

    def test_frequent_language_moves_up_but_english_stays_first(self, repo, ai_service):
        repo.create(Word(term="Haus", language="de"))
        repo.create(Word(term="gehen", language="de"))
        provider = _LanguageAwareProvider(known={})
        provider.candidates = ["en", "fr", "de"]
        service = WordService(repo, ai_service, open_dictionary=provider)

        # de kütüphanede baskın → fr'nin önüne; en zengin kaynak olarak başta.
        assert service.detect_languages("x") == ["en", "de", "fr"]

    def test_prior_reorders_when_no_english(self, repo, ai_service):
        repo.create(Word(term="Haus", language="de"))
        provider = _LanguageAwareProvider(known={})
        provider.candidates = ["fr", "de"]
        service = WordService(repo, ai_service, open_dictionary=provider)

        assert service.detect_languages("x") == ["de", "fr"]

    def test_empty_library_keeps_original_order(self, repo, ai_service):
        provider = _LanguageAwareProvider(known={})
        provider.candidates = ["en", "fr", "de"]
        service = WordService(repo, ai_service, open_dictionary=provider)

        assert service.detect_languages("x") == ["en", "fr", "de"]

    def test_single_candidate_skips_the_prior(self, repo, ai_service):
        repo.create(Word(term="Haus", language="de"))
        provider = _LanguageAwareProvider(known={})
        provider.candidates = ["ru"]
        service = WordService(repo, ai_service, open_dictionary=provider)

        assert service.detect_languages("хлеб") == ["ru"]

    def test_detect_language_singular_uses_the_prior(self, repo, ai_service):
        """Tekil detect_language de önseli görmeli (İngilizcesiz, çok aday)."""
        repo.create(Word(term="Haus", language="de"))
        provider = _LanguageAwareProvider(known={})
        provider.candidates = ["fr", "de"]
        service = WordService(repo, ai_service, open_dictionary=provider)

        assert service.detect_language("x") == "de"

    def test_demoted_english_does_not_return_to_the_front(self, repo, ai_service):
        """
        Açık sözlüğün bilinçli olarak geride bıraktığı İngilizce, kütüphane
        önceliğiyle tekrar başa dönmemeli.

        Gerçek vaka: "bonjour" gibi ödünç selamlarda OpenDictionaryService
        Fransızca'yı öne alıyor (ince İngilizce çeviri notuna karşı). Kullanıcının
        kütüphanesinde Fransızcadan çok İngilizce kelime varsa, eski "yalnızca
        candidates[0] == 'en' ise sabitle" kuralı bu kararı sessizce geçersiz
        kılıp İngilizce'yi tekrar başa taşırdı.
        """
        for i in range(5):
            repo.create(Word(term=f"word{i}", language="en"))
        provider = _LanguageAwareProvider(known={})
        provider.candidates = ["fr", "en"]  # açık sözlük zaten fr'yi öne almış
        service = WordService(repo, ai_service, open_dictionary=provider)

        assert service.detect_languages("Bonjour") == ["fr", "en"]


class TestApplyContent:
    def test_missing_fields_keep_existing_values(self, word_service: WordService):
        """Açık sözlük bazı alanları boş bırakabilir; mevcut içeriği silmemeli."""
        word = word_service.add_word(
            "ephemeral",
            "en",
            ai_data={
                "definition": "eski tanım",
                "usage_notes": "eski not",
                "synonyms": ["a", "b"],
            },
        )

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


class _LanguageAwareProvider:
    """
    Yalnızca belirli dillerde kelimeyi 'bilen' sahte sağlayıcı.

    Gerçek sağlayıcılar gibi, bilmediği dilde ContentProviderError fırlatır.
    """

    def __init__(self, known: dict[str, str]) -> None:
        self._known = known  # dil kodu -> tanım
        self.candidates: list[str] = ["en"]
        self.calls: list[tuple[str, str]] = []
        self.explode: Exception | None = None

    @property
    def is_configured(self) -> bool:
        return True

    def detect_languages(self, term: str) -> list[str]:
        return self.candidates

    def generate_word_data(self, term: str, language: str = "en") -> dict:
        self.calls.append((term, language))
        if self.explode is not None:
            raise self.explode
        if language not in self._known:
            raise ContentProviderError(f"'{term}' {language} dilinde yok.")
        return {"definition": self._known[language]}
