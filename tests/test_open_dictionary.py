"""
Lexis — Tests: Açık sözlük servisi (anahtarsız içerik)

Ağa çıkılmaz: tüm HTTP çağrıları sahte yanıtlarla değiştirilir.
"""

import pytest

from lexis.domain.exceptions import ContentProviderError
from lexis.services import open_dictionary as od
from lexis.services.open_dictionary import OpenDictionaryService

# ── Sahte yanıtlar ────────────────────────────────────────────────────────

DICTIONARY_RESPONSE = [
    {
        "word": "ephemeral",
        "phonetic": "/əˈfɛmərəl/",
        "phonetics": [
            {"text": "/əˈfɛmərəl/", "audio": "https://example.org/ephemeral.mp3"},
        ],
        "meanings": [
            {
                "partOfSpeech": "adjective",
                "synonyms": ["fleeting", "transient"],
                "antonyms": ["permanent"],
                "definitions": [
                    {
                        "definition": "Lasting for a very short time.",
                        "synonyms": [],
                        "antonyms": [],
                    },
                    {
                        "definition": "Existing for only one day.",
                        "synonyms": ["daily"],
                        "antonyms": [],
                    },
                ],
            }
        ],
    }
]

WIKTIONARY_RESPONSE = {
    "de": [
        {
            "partOfSpeech": "Noun",
            "language": "German",
            "definitions": [{"definition": '<a rel="mw:WikiLink" href="/wiki/house">house</a>'}],
        }
    ],
    "en": [{"partOfSpeech": "Proper noun", "definitions": [{"definition": "A surname"}]}],
}

TATOEBA_RESPONSE = {
    "results": [
        {
            "text": "Love's pleasure is ephemeral.",
            "lang": "eng",
            "translations": [[{"lang": "tur", "text": "Aşkın zevki geçicidir."}]],
        }
    ]
}


@pytest.fixture
def fake_network(monkeypatch):
    """
    Tüm dış çağrıları yönlendirir. Test, hangi uca ne döneceğini
    `routes` sözlüğüyle belirler.
    """
    routes: dict[str, object] = {}

    def fake_get_json(url: str, params: dict | None = None):
        for key, value in routes.items():
            if key in url:
                return value(params) if callable(value) else value
        return None

    monkeypatch.setattr(od, "_get_json", fake_get_json)
    return routes


@pytest.fixture
def service() -> OpenDictionaryService:
    return OpenDictionaryService()


# ── Temel davranış ────────────────────────────────────────────────────────


def test_is_always_configured(service):
    """Anahtar gerektirmez: her zaman kullanılabilir olmalı."""
    assert service.is_configured is True


def test_english_word_collects_full_content(service, fake_network):
    fake_network["dictionaryapi.dev"] = DICTIONARY_RESPONSE
    fake_network["tatoeba"] = TATOEBA_RESPONSE
    fake_network["mymemory"] = {
        "responseStatus": 200,
        "responseData": {"translatedText": "Çok kısa süre süren."},
    }

    data = service.generate_word_data("ephemeral", "en")

    assert data["definition_short"] == "Çok kısa süre süren."
    assert data["part_of_speech"] == "adjective"
    assert data["synonyms"] == ["fleeting", "transient", "daily"]
    assert data["antonyms"] == ["permanent"]
    assert data["phonetic"] == "/əˈfɛmərəl/"
    assert data["audio_url"] == "https://example.org/ephemeral.mp3"
    assert data["example_sentences"] == ["Love's pleasure is ephemeral.\nAşkın zevki geçicidir."]


def test_non_english_word_uses_wiktionary(service, fake_network):
    fake_network["wiktionary"] = WIKTIONARY_RESPONSE
    fake_network["mymemory"] = {
        "responseStatus": 200,
        "responseData": {"translatedText": "ev"},
    }

    data = service.generate_word_data("Haus", "de")

    assert data["definition_short"] == "ev"
    assert data["part_of_speech"] == "Noun"


def test_wiktionary_html_is_stripped(service, fake_network):
    """Wiktionary tanımları HTML içerir; kullanıcıya düz metin gitmeli."""
    fake_network["wiktionary"] = WIKTIONARY_RESPONSE
    fake_network["mymemory"] = None  # çeviri yok → özgün metne düşer

    data = service.generate_word_data("Haus", "de")

    assert data["definition_short"] == "house"
    assert "<" not in data["definition_short"]


def test_wiktionary_only_uses_requested_language(service, fake_network):
    """Yanıt birçok dil içerir; yalnızca istenen dilin bölümü alınmalı."""
    fake_network["wiktionary"] = WIKTIONARY_RESPONSE
    fake_network["mymemory"] = None

    data = service.generate_word_data("Haus", "de")

    assert "surname" not in data["definition_short"]  # 'en' bölümü sızmamalı


def test_unknown_word_raises(service, fake_network):
    fake_network["dictionaryapi.dev"] = []

    with pytest.raises(ContentProviderError, match="bulunamadı"):
        service.generate_word_data("zzzqqxyz", "en")


def test_unsupported_language_raises(service, fake_network):
    """Wiktionary'de o dilde bölüm yoksa anlaşılır hata verilmeli."""
    fake_network["wiktionary"] = {"en": [{"definitions": [{"definition": "x"}]}]}

    with pytest.raises(ContentProviderError):
        service.generate_word_data("Haus", "sv")


# ── Dayanıklılık: tek kaynak düşerse kelime yine eklenebilmeli ────────────


def test_translation_failure_falls_back_to_source_text(service, fake_network):
    fake_network["dictionaryapi.dev"] = DICTIONARY_RESPONSE
    fake_network["mymemory"] = None  # çeviri servisi ölü

    data = service.generate_word_data("ephemeral", "en")

    assert data["definition_short"] == "Lasting for a very short time."
    assert "açık sözlük" in data["usage_notes"]  # kullanıcı kaynağı bilsin


def test_examples_failure_leaves_word_usable(service, fake_network):
    fake_network["dictionaryapi.dev"] = DICTIONARY_RESPONSE
    fake_network["mymemory"] = {
        "responseStatus": 200,
        "responseData": {"translatedText": "Kısa süreli."},
    }
    fake_network["tatoeba"] = None  # örnek servisi ölü

    data = service.generate_word_data("ephemeral", "en")

    assert data["example_sentences"] == []
    assert data["definition_short"] == "Kısa süreli."


def test_example_without_translation_still_included(service, fake_network):
    fake_network["dictionaryapi.dev"] = DICTIONARY_RESPONSE
    fake_network["mymemory"] = None
    fake_network["tatoeba"] = {
        "results": [{"text": "An ephemeral joy.", "lang": "eng", "translations": []}]
    }

    data = service.generate_word_data("ephemeral", "en")

    assert data["example_sentences"] == ["An ephemeral joy."]


def test_translation_source_is_always_english(service, fake_network, monkeypatch):
    """
    Kaynaklar tanımı daima İngilizce verir; çeviri çifti de en|tr olmalı.
    (Aksi hâlde 'Haus' için de|tr denenip metin çevrilmeden geri dönüyordu.)
    """
    seen: dict = {}

    def capture(url, params=None):
        if "mymemory" in url:
            seen.update(params or {})
            return {"responseStatus": 200, "responseData": {"translatedText": "ev"}}
        if "wiktionary" in url:
            return WIKTIONARY_RESPONSE
        return None

    monkeypatch.setattr(od, "_get_json", capture)

    service.generate_word_data("Haus", "de")

    assert seen["langpair"] == "en|tr"


def test_overlong_definition_is_not_sent_to_translator(service, fake_network):
    """MyMemory'nin kotasını korumak için çok uzun metin çevrilmez."""
    long_def = "x " * 400
    fake_network["dictionaryapi.dev"] = [
        {"meanings": [{"partOfSpeech": "noun", "definitions": [{"definition": long_def}]}]}
    ]
    fake_network["mymemory"] = {
        "responseStatus": 200,
        "responseData": {"translatedText": "ÇEVRİLDİ"},
    }

    data = service.generate_word_data("uzun", "en")

    assert "ÇEVRİLDİ" not in data["definition_short"]


# ── Yardımcılar ───────────────────────────────────────────────────────────


def test_unique_preserves_order_and_drops_case_duplicates():
    assert od._unique(["Fleeting", "fleeting", "transient", " "]) == ["Fleeting", "transient"]


def test_strip_html_collapses_whitespace():
    assert od._strip_html("<b>bir</b>  <i>iki</i>\n üç") == "bir iki üç"


def test_get_json_returns_none_on_network_error(monkeypatch):
    """Ağ hatası istisna fırlatmamalı; çağıran None görüp devam edebilmeli."""

    def boom(*a, **k):
        raise OSError("ağ yok")

    monkeypatch.setattr(od.urllib.request, "urlopen", boom)
    assert od._get_json("https://example.org") is None
