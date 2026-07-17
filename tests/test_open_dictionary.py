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
        "responseData": {"translatedText": "Çok kısa süre süren.", "match": 0.9},
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
        "responseData": {"translatedText": "ev", "match": 0.9},
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


def test_english_falls_back_to_wiktionary_when_dictionaryapi_has_no_entry(service, fake_network):
    """
    dictionaryapi.dev argo/az bilinen kelimelerde (örn. "yeet", "rizz") 404
    veriyor; Wiktionary'nin İngilizce bölümü yedek olarak denenmeli.
    """
    fake_network["dictionaryapi.dev"] = []  # 404 → boş liste
    fake_network["wiktionary"] = WIKTIONARY_RESPONSE
    fake_network["mymemory"] = None

    data = service.generate_word_data("surname-ish-slang", "en")

    assert data["definition_short"] == "A surname"
    assert data["part_of_speech"] == "Proper noun"


# ── "Şunu mu demek istediniz?" önerileri ──────────────────────────────────


def _datamuse(routes, *, sl: list[str], sp: list[str]) -> None:
    """
    Datamuse'un iki ucunu ayrı ayrı yanıtlar (sl: okunuş, sp: yazım).

    Not: gerçek API, sorgu kendi sözlüğündeyse onu ilk sırada döndürür —
    yanlış yazımlar da sözlüğünde olduğu için bu sık görülür. Sahte yanıtlar
    bu davranışı taklit etmeli, yoksa sıralama testleri yanıltıcı olur.
    """

    def respond(params):
        words = sl if "sl" in (params or {}) else sp
        return [{"word": w, "score": 100} for w in words]

    routes["datamuse"] = respond


def test_suggestions_prefer_source_order_over_string_similarity(service, fake_network):
    """
    Kaynağın alaka sıralaması korunmalı.

    Benzerliğe göre yeniden sıralamak ölçüldü ve daha kötüydü: "freind" için
    harfçe yakın ama uydurma olan "frind"/"feind", gerçek düzeltme "friend"i
    listenin dışına itiyordu.
    """
    _datamuse(
        fake_network,
        sl=["freind", "friend", "freund"],
        sp=["freind", "frind", "feind"],
    )

    assert service.suggest_terms("freind", "en")[0] == "Friend"


def test_suggestions_exclude_the_query_itself(service, fake_network):
    """Datamuse sözlüğünde yanlış yazımlar da var; sorgunun kendisi öneri değil."""
    _datamuse(fake_network, sl=["recieve", "receive"], sp=["recieve"])

    suggestions = service.suggest_terms("recieve", "en")

    assert "recieve" not in [s.casefold() for s in suggestions]
    assert "Receive" in suggestions


def test_suggestions_drop_unrelated_words(service, fake_network):
    """Benzerlik eşiği alakasız adayları elemeli."""
    _datamuse(fake_network, sl=["zebra", "helicopter"], sp=["xylophone"])

    assert service.suggest_terms("recieve", "en") == []


def test_suggestions_are_capped(service, fake_network):
    """Arayüzü boğmamak için öneri sayısı sınırlı."""
    _datamuse(fake_network, sl=[f"receiv{i}" for i in range(20)], sp=[])

    assert len(service.suggest_terms("recieve", "en")) <= od.MAX_SUGGESTIONS


def test_non_english_suggestions_use_wiktionary(service, fake_network):
    """Datamuse yalnızca İngilizce; diğer diller opensearch'e düşer."""
    fake_network["api.php"] = ["Haus", ["Hause", "Hauser", "Haustier"], [], []]

    suggestions = service.suggest_terms("Haus", "de")

    assert "Hause" in suggestions


def test_completion_uses_the_autocomplete_endpoint(service, fake_network):
    """
    Yazarken /sug kullanılmalı, sp/sl değil.

    Ölçüldü: yarım kelimede sp çöp veriyor ("ephem" → epher, phem), /sug ilk
    sırada "ephemeral" veriyor.
    """
    seen: list[str] = []

    def respond(params):
        seen.append("sug" if "s" in (params or {}) else "words")
        return [{"word": "ephemeral"}, {"word": "ephemera"}]

    fake_network["datamuse.com/sug"] = respond

    assert service.complete_terms("ephem", "en") == ["Ephemeral", "Ephemera"]
    assert seen == ["sug"]


def test_completion_keeps_longer_words_that_similarity_would_drop(service, fake_network):
    """
    Tamamlamada benzerlik eşiği uygulanmamalı.

    Tamamlanan kelime yazılandan uzun olduğu için oran düşük çıkıyor:
    "ephem" → "ephemerality" oranı 0.59, yani eşik geçerli bir tamamlamayı
    elerdi.
    """
    fake_network["datamuse.com/sug"] = [{"word": "ephemerality"}]

    assert service.complete_terms("ephem", "en") == ["Ephemerality"]


def test_completion_needs_a_few_letters(service, fake_network):
    """Tek harfte her kelime eşleşir; ağa çıkmadan boş dönülmeli."""
    calls: list = []
    fake_network["datamuse"] = lambda params: calls.append(params) or []

    assert service.complete_terms("ep", "en") == []
    assert calls == []


def test_completion_excludes_the_query_itself(service, fake_network):
    """/sug tam eşleşmeyi de döndürür; yazılan kelimeyi önermenin anlamı yok."""
    fake_network["datamuse.com/sug"] = [{"word": "thug"}, {"word": "thugs"}]

    assert service.complete_terms("thug", "en") == ["Thugs"]


def test_non_english_completion_uses_wiktionary(service, fake_network):
    fake_network["api.php"] = ["Hau", ["Haus", "Hause"], [], []]

    assert service.complete_terms("Hau", "de") == ["Haus", "Hause"]


def test_suggestions_are_capitalized(service, fake_network):
    """Öneriler baş harfi büyük gösterilir (kullanıcı tercihi)."""
    _datamuse(fake_network, sl=["receive", "relieve"], sp=[])

    assert service.suggest_terms("recieve", "en") == ["Receive", "Relieve"]


def test_capitalizing_keeps_the_rest_of_the_word(service, fake_network):
    """
    Yalnızca baş harf büyütülür.

    str.capitalize() kalanı küçültüp "USA" → "Usa" yapardı.
    """
    fake_network["datamuse.com/sug"] = [{"word": "iPhone"}, {"word": "USA"}]

    # "USA" olduğu gibi kalmalı; str.capitalize() onu "Usa" yapardı.
    assert service.complete_terms("ipho", "en") == ["IPhone", "USA"]


# ── Dil algılama ──────────────────────────────────────────────────────────


def test_detect_languages_returns_all_supported_candidates(service, fake_network):
    """
    Tek dil değil aday listesi: çağıran ilk tahminde pes etmesin.

    Gerçek vaka: Wiktionary "Baran" için ['en', 'other', 'pl', 'sk', 'tr']
    veriyor — İngilizce'de soyadı, Lehçe'de "koç". Yalnızca ilk adayı denemek
    haksız "bulunamadı" üretiyordu.
    """
    fake_network["definition"] = {"en": [{}], "other": [{}], "pl": [{}], "sk": [{}]}

    # 'other' ve 'sk' uygulamada desteklenmiyor; aday olmamalılar.
    assert service.detect_languages("Baran") == ["en", "pl"]


def test_detect_languages_puts_english_first(service, fake_network):
    """İngilizce en olası kullanım ve telaffuz veren tek zengin kaynak."""
    fake_network["definition"] = {"pl": [{}], "de": [{}], "en": [{}]}

    assert service.detect_languages("baran")[0] == "en"


def test_detect_languages_is_not_capped(service, fake_network):
    """
    Adaylar kesilmez ("her dil için sorgulasın"): sayfa önbelleği sayesinde ek
    aday ek ağ isteği getirmiyor. Gemini'nin ücretli denemelerini WordService
    kendi sınırıyla korur.
    """
    fake_network["definition"] = dict.fromkeys(["en", "de", "fr", "es", "it", "pl"], [{}])

    assert service.detect_languages("word") == ["en", "de", "fr", "es", "it", "pl"]


def test_detect_languages_retries_lowercase_when_exact_case_misses(service, fake_network):
    """
    Wiktionary büyük/küçük harfe duyarlı: "Tahanan" 404 verirken "tahanan"
    bulunuyor. Küçük harf denenmezse kullanıcı haksız "bulunamadı" görüyordu.
    """
    fake_network["definition/tahanan"] = {"de": [{}], "pl": [{}]}

    assert service.detect_languages("Tahanan") == ["de", "pl"]


def test_lowercase_term_is_not_fetched_twice(service, fake_network):
    """Zaten küçük harfli terimde ikinci bir deneme anlamsız."""
    calls: list = []
    fake_network["definition"] = lambda params: calls.append(1) or None

    service.detect_languages("tahanan")

    assert calls == [1]


def test_wiktionary_page_is_fetched_once_across_detection_and_generation(service, fake_network):
    """
    Dil algılama ve aday dillerdeki üretim aynı Wiktionary sayfasını kullanır.

    Önbellek olmadan her aday dil için sayfa yeniden çekiliyordu; aday sayısı
    kadar gereksiz ağ gecikmesi birikiyordu.
    """
    calls: list = []
    fake_network["definition"] = lambda params: calls.append(1) or WIKTIONARY_RESPONSE
    fake_network["mymemory"] = None

    candidates = service.detect_languages("Haus")
    service.generate_word_data("Haus", "de")

    assert candidates == ["en", "de"]
    assert calls == [1]


def test_detect_language_prefers_english_when_present(service, fake_network):
    """
    Çok dilli kelimelerde İngilizce tercih edilir.

    Ölçüldü: Wiktionary "Haus" için ['en', 'bar', 'other', 'de', ...] veriyor —
    yani tahmin kesin olamaz. İngilizce hem en olası kullanım, hem de telaffuz
    ve ses veren tek zengin kaynağa (dictionaryapi.dev) bağlanıyor. Arayüz
    kaydetmeden önce düzeltme imkânı sunuyor.
    """
    fake_network["definition"] = {"en": [{}], "de": [{}], "bar": [{}]}

    assert service.detect_language("Haus") == "en"


def test_detect_language_picks_the_only_supported_one(service, fake_network):
    fake_network["definition"] = {"other": [{}], "de": [{}], "li": [{}]}

    assert service.detect_language("gehen") == "de"


def test_detect_language_ignores_unsupported_languages(service, fake_network):
    """Uygulamanın desteklemediği diller aday olmamalı."""
    fake_network["definition"] = {"ga": [{}], "gd": [{}]}

    assert service.detect_language("thug") == "en"  # desteklenen yok → varsayılan


def test_detect_language_falls_back_when_word_is_unknown(service, fake_network):
    """Wiktionary bulamazsa (ağ hatası dâhil) İngilizce varsayılır."""
    assert service.detect_language("zzzqqxyz") == "en"


def test_detect_language_of_empty_term_makes_no_request(service, fake_network):
    calls: list = []
    fake_network["definition"] = lambda params: calls.append(1) or {}

    assert service.detect_language("  ") == "en"
    assert calls == []


def test_suggestion_network_failure_returns_empty(service, fake_network):
    """Öneri bir kolaylık: ağ düşerse kelime ekleme akışı bloklanmamalı."""
    assert service.suggest_terms("recieve", "en") == []


def test_empty_term_makes_no_request(service, fake_network):
    calls: list = []
    fake_network["datamuse"] = lambda params: calls.append(params) or []

    assert service.suggest_terms("   ", "en") == []
    assert calls == []


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
        "responseData": {"translatedText": "Kısa süreli.", "match": 0.9},
    }
    fake_network["tatoeba"] = None  # örnek servisi ölü

    data = service.generate_word_data("ephemeral", "en")

    assert data["example_sentences"] == []
    assert data["definition_short"] == "Kısa süreli."


def test_low_confidence_translation_is_rejected(service, fake_network):
    """
    MyMemory'nin çeviri belleği bazen alakasız eşleşmeler döndürür (düşük
    match skoru). Bunları göstermek yerine İngilizce orijinale düşülmeli.
    """
    fake_network["dictionaryapi.dev"] = DICTIONARY_RESPONSE
    fake_network["mymemory"] = {
        "responseStatus": 200,
        "responseData": {"translatedText": "Alakasız çeviri.", "match": 0.3},
    }

    data = service.generate_word_data("ephemeral", "en")

    assert data["definition_short"] == "Lasting for a very short time."


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
            return {"responseStatus": 200, "responseData": {"translatedText": "ev", "match": 0.9}}
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
