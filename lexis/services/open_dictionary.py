"""
Lexis — Açık Sözlük Servisi (API anahtarı gerektirmez)

Kelime içeriğini üretken bir modelden değil, gerçek sözlük kaynaklarından
toplar. Böylece uygulama kutudan çıktığı gibi, hiçbir anahtar girilmeden
çalışır ve tanımlar uydurma olmaz.

Kaynaklar (hiçbiri anahtar istemez):
  • dictionaryapi.dev — İngilizce tanım, tür, eş/zıt anlam, fonetik, telaffuz
  • Wiktionary REST  — diğer diller için tanım ve tür
  • Tatoeba          — örnek cümleler ve hazır Türkçe çevirileri
  • MyMemory         — tanımın Türkçeye çevirisi

Arayüzü AIService ile aynıdır (generate_word_data), böylece WordService
ikisini de aynı şekilde çağırabilir.
"""

from __future__ import annotations

import difflib
import json
import logging
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from itertools import zip_longest

from lexis.domain.exceptions import ContentProviderError
from lexis.domain.models import SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)

USER_AGENT = "Lexis/0.1 (https://github.com/talhacaglar/lexis)"
TIMEOUT_SECONDS = 12

DICTIONARY_API = "https://api.dictionaryapi.dev/api/v2/entries/en/{term}"
WIKTIONARY_API = "https://en.wiktionary.org/api/rest_v1/page/definition/{term}"
TATOEBA_API = "https://tatoeba.org/en/api_v0/search"
MYMEMORY_API = "https://api.mymemory.translated.net/get"
DATAMUSE_API = "https://api.datamuse.com/words"
DATAMUSE_SUGGEST_API = "https://api.datamuse.com/sug"
WIKTIONARY_SEARCH_API = "https://en.wiktionary.org/w/api.php"

# dictionaryapi.dev pratikte yalnızca İngilizce sunuyor (diğer dil uçları 404).
RICH_LANGUAGE = "en"

MAX_SYNONYMS = 5
MAX_ANTONYMS = 4
MAX_EXAMPLES = 3

# "Şunu mu demek istediniz?" önerileri
MAX_SUGGESTIONS = 5
SUGGESTION_POOL = 15
# Yazarken tamamlama için en az bu kadar harf gerekir; daha kısası her kelimeyi
# eşleştirip gürültü üretir.
MIN_COMPLETION_CHARS = 3

# Benzerlik eşiği: altındakiler yazım hatası değil, alakasız kelimelerdir.
# Ölçüldü: 0.6 "seperate→separate" (0.88) ve "Hause→house" (0.80) gibi gerçek
# düzeltmeleri geçirirken alakasızları eler.
MIN_SIMILARITY = 0.6

# MyMemory'nin anonim kotasını tüketmemek için yalnızca kısa metin çevrilir.
MAX_TRANSLATE_CHARS = 480


class _HTMLStripper(HTMLParser):
    """Wiktionary tanımları HTML işaretlemesi içerir; düz metne indirger."""

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    @property
    def text(self) -> str:
        return " ".join("".join(self._parts).split())


def _strip_html(raw: str) -> str:
    stripper = _HTMLStripper()
    stripper.feed(raw)
    return stripper.text


def _get_json(url: str, params: dict | None = None) -> object:
    """
    Basit GET + JSON ayrıştırma.

    Ağ hataları çağırana ContentProviderError olarak değil, None olarak döner;
    tek bir kaynağın düşmesi tüm üretimi engellememeli.
    """
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
        logger.info("Kaynak yanıt vermedi (%s): %s", url.split("?")[0], e)
        return None


def _strip_diacritics(text: str) -> str:
    """Aksanları kaldırır ('café' → 'cafe'): aksanlı yazılan terimin ASCII karşılığı."""
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def _term_variants(term: str):
    """
    Wiktionary'de denenecek yazım varyantlarını sırayla, tekrarsız üretir.

    Wiktionary büyük/küçük harfe ve aksana duyarlı. Küçük harf denemesi baş harfi
    büyük terimleri ("Tahanan" → "tahanan"), aksan temizleme ise aksanlı yazılıp
    ASCII başlık altında bulunan terimleri ("Café" → "cafe") yakalar. ASCII ve
    küçük harfli bir terimde liste tek elemana iner — gereksiz istek olmaz.
    """
    seen: set[str] = set()
    for variant in (term, term.lower(), _strip_diacritics(term), _strip_diacritics(term).lower()):
        if variant and variant not in seen:
            seen.add(variant)
            yield variant


MIN_TRANSLATION_MATCH = 0.5


def _translate_to_turkish(text: str) -> str:
    """
    İngilizce tanımı Türkçeye çevirir.

    Kaynak daima İngilizce'dir: hem dictionaryapi.dev hem de en.wiktionary,
    kelimenin dili ne olursa olsun tanımları İngilizce verir.

    Başarısızlıkta veya düşük güvenilirlikli eşleşmede boş string döner;
    çağıran taraf bu durumda İngilizce orijinal metne düşer. MyMemory'nin
    çeviri belleği bazen tamamen alakasız eşleşmeler döndürür (match skoru
    düşük) — bunları göstermek yanlış öğretmekten beter.
    """
    text = text.strip()
    if not text or len(text) > MAX_TRANSLATE_CHARS:
        return ""

    data = _get_json(MYMEMORY_API, {"q": text, "langpair": "en|tr"})
    if not isinstance(data, dict):
        return ""
    if data.get("responseStatus") != 200:
        return ""
    response_data = data.get("responseData") or {}
    try:
        match = float(response_data.get("match", 0))
    except (TypeError, ValueError):
        match = 0.0
    if match < MIN_TRANSLATION_MATCH:
        return ""
    translated = response_data.get("translatedText") or ""
    return translated.strip()


def _fetch_english(term: str) -> dict:
    """dictionaryapi.dev'den zengin İngilizce kaydı çeker."""
    data = _get_json(DICTIONARY_API.format(term=urllib.parse.quote(term)))
    if not isinstance(data, list) or not data:
        return {}

    entry = data[0]
    definitions: list[str] = []
    synonyms: list[str] = []
    antonyms: list[str] = []
    part_of_speech = ""

    for meaning in entry.get("meanings", []):
        if not part_of_speech:
            part_of_speech = meaning.get("partOfSpeech", "")
        synonyms.extend(meaning.get("synonyms", []))
        antonyms.extend(meaning.get("antonyms", []))
        for d in meaning.get("definitions", []):
            if d.get("definition"):
                definitions.append(d["definition"])
            synonyms.extend(d.get("synonyms", []))
            antonyms.extend(d.get("antonyms", []))

    phonetic = entry.get("phonetic", "")
    audio_url = ""
    for p in entry.get("phonetics", []):
        if not phonetic and p.get("text"):
            phonetic = p["text"]
        if not audio_url and p.get("audio"):
            audio_url = p["audio"]

    return {
        "definitions": definitions,
        "part_of_speech": part_of_speech,
        "synonyms": _unique(synonyms)[:MAX_SYNONYMS],
        "antonyms": _unique(antonyms)[:MAX_ANTONYMS],
        "phonetic": phonetic,
        "audio_url": audio_url,
    }


def _fetch_examples(term: str, language: str) -> list[str]:
    """
    Tatoeba'dan örnek cümleleri ve hazır Türkçe çevirilerini çeker.

    'foreign\\nturkish' biçimi uygulamanın beklediği formattır.
    """
    tatoeba_lang = _TATOEBA_LANGS.get(language)
    if not tatoeba_lang:
        return []

    data = _get_json(
        TATOEBA_API,
        {"from": tatoeba_lang, "to": "tur", "query": term, "limit": MAX_EXAMPLES * 2},
    )
    if not isinstance(data, dict):
        return []

    examples: list[str] = []
    for result in data.get("results", [])[: MAX_EXAMPLES * 2]:
        foreign = (result.get("text") or "").strip()
        if not foreign:
            continue
        turkish = ""
        # Çeviriler iç içe listeler hâlinde gelir.
        for group in result.get("translations", []):
            for t in group:
                if t.get("lang") == "tur" and t.get("text"):
                    turkish = t["text"].strip()
                    break
            if turkish:
                break
        examples.append(f"{foreign}\n{turkish}" if turkish else foreign)
        if len(examples) >= MAX_EXAMPLES:
            break

    return examples


def _datamuse_words(param: str, term: str) -> list[str]:
    data = _get_json(DATAMUSE_API, {param: term, "max": SUGGESTION_POOL})
    if not isinstance(data, list):
        return []
    return [d["word"] for d in data if isinstance(d, dict) and d.get("word")]


def _capitalize(word: str) -> str:
    """
    Baş harfi büyütür, gerisine dokunmaz.

    str.capitalize() kullanılmaz: o, kelimenin kalanını küçültüp "USA" → "Usa"
    gibi kısaltmaları bozar.
    """
    return word[:1].upper() + word[1:]


def _interleave(primary: list[str], secondary: list[str]) -> list[str]:
    """
    İki listeyi sıralarını koruyarak dönüşümlü birleştirir.

    Her iki kaynağın kendi alaka sıralaması korunur; birinin başındaki güçlü
    aday, diğerinin kuyruğundaki zayıf adayın arkasında kalmaz.
    """
    merged: list[str] = []
    for a, b in zip_longest(primary, secondary):
        if a is not None:
            merged.append(a)
        if b is not None:
            merged.append(b)
    return merged


def _suggest_english(term: str) -> list[str]:
    """
    Datamuse'tan okunuşu ve yazımı benzer kelimeleri çeker.

    İki uç birlikte kullanılır çünkü tek başına ikisi de yetersiz (ölçüldü):
      • sp (yazım) harf yer değiştirmesini kaçırır: "recieve" → receive YOK
      • sl (okunuş) onu yakalar: "recieve" → receive, "freind" → friend

    Okunuş önce geliyor: yazım hatalarının çoğu sesi koruyor, dolayısıyla sl'in
    ilk sonuçları sp'ninkilerden isabetli (ölçüldü: "freind" için sp yalnızca
    "frind"/"feind" gibi uydurma komşular veriyor, friend'i sl buluyor).

    Yalnızca İngilizce, ama yazım düzeltmede Wiktionary'nin önek aramasından
    belirgin biçimde iyi: "seperate" → separate; Wiktionary "seperated" veriyor.
    """
    return _interleave(_datamuse_words("sl", term), _datamuse_words("sp", term))


def _suggest_wiktionary(term: str) -> list[str]:
    """
    Wiktionary'nin opensearch ucundan başlık önerileri çeker.

    İngilizce dışındaki diller için tek anahtarsız seçenek. Yanıt biçimi:
    [sorgu, [başlıklar], [açıklamalar], [bağlantılar]]
    """
    data = _get_json(
        WIKTIONARY_SEARCH_API,
        {"action": "opensearch", "search": term, "limit": SUGGESTION_POOL, "format": "json"},
    )
    if not isinstance(data, list) or len(data) < 2 or not isinstance(data[1], list):
        return []
    return [t for t in data[1] if isinstance(t, str)]


def _complete_english(prefix: str) -> list[str]:
    """
    Datamuse'un /sug ucundan tamamlama önerileri çeker.

    Yazarken kullanılan uç budur; sp/sl yarım kelimede işe yaramıyor (ölçüldü:
    "ephem" için sp "epher", "phem", "echem" gibi çöp veriyor, /sug ise ilk
    sırada "ephemeral" veriyor).
    """
    data = _get_json(DATAMUSE_SUGGEST_API, {"s": prefix, "max": SUGGESTION_POOL})
    if not isinstance(data, list):
        return []
    return [d["word"] for d in data if isinstance(d, dict) and d.get("word")]


def _pick_suggestions(
    term: str, candidates: list[str], min_similarity: float | None = None
) -> list[str]:
    """
    Adaylardan öneri listesi kurar: sorgunun kendisini ve yinelenenleri atar,
    kaynağın alaka sıralamasını korur, baş harfi büyütür.

    min_similarity verilirse benzerlik bir *filtre* olarak uygulanır, sıralama
    ölçütü değil ("şunu mu demek istediniz?" düzeltmeleri): benzerliğe göre
    yeniden sıralamayı ölçtüm, daha kötüydü — "freind" için harfçe yakın ama
    uydurma "frind"/"feind", gerçek düzeltme "friend"i ilk beşin dışına itiyordu.

    Tamamlamada (min_similarity=None) eşik uygulanmaz: tamamlanan kelime yazılandan
    uzun olduğu için oran düşük çıkıyor (ölçüldü: "ephem" → "ephemerality" 0.59) ve
    geçerli bir tamamlama elenirdi.

    Kelimenin kendisi öneri değildir: Datamuse sözlüğünde yanlış yazımlar da
    bulunduğu için sorgunun kendisi sonuçlarda dönebiliyor.
    """
    key = term.strip().casefold()
    out: list[str] = []
    seen: set[str] = set()

    for candidate in candidates:
        c_key = candidate.strip().casefold()
        if not c_key or c_key == key or c_key in seen:
            continue
        seen.add(c_key)
        similar = (
            min_similarity is None
            or difflib.SequenceMatcher(None, key, c_key).ratio() >= min_similarity
        )
        if similar:
            out.append(_capitalize(candidate.strip()))
        if len(out) >= MAX_SUGGESTIONS:
            break

    return out


def _unique(items: list[str]) -> list[str]:
    """Sırayı koruyarak yinelenenleri atar."""
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip().casefold()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out


# Uygulama dil kodları → Tatoeba'nın ISO 639-3 kodları.
_TATOEBA_LANGS = {
    "en": "eng",
    "de": "deu",
    "fr": "fra",
    "es": "spa",
    "it": "ita",
    "pt": "por",
    "ja": "jpn",
    "zh": "cmn",
    "ko": "kor",
    "ar": "ara",
    "ru": "rus",
    "nl": "nld",
    "pl": "pol",
    "sv": "swe",
}


def _script_hint(term: str) -> list[str]:
    """
    Latin dışı alfabelerden ağa çıkmadan dil adayı çıkarır.

    Kiril/Hangul/Arap/Kana kesin sinyaldir: bu betikteki bir kelime İngilizce
    olamaz. Ağ düştüğünde ya da Wiktionary kaydı olmadığında kör "en" yerine
    doğru dile düşmeyi sağlar. Han (CJK) Çince ve Japoncada ortak olduğundan iki
    aday döner. Latin metinde ayırt edici sinyal yok → boş liste.
    """
    has_han = False
    for ch in term:
        code = ord(ch)
        if 0x3040 <= code <= 0x30FF:  # Hiragana/Katakana → kesin Japonca
            return ["ja"]
        if 0x0400 <= code <= 0x04FF:  # Kiril
            return ["ru"]
        if 0x0600 <= code <= 0x06FF:  # Arap
            return ["ar"]
        if 0xAC00 <= code <= 0xD7A3 or 0x1100 <= code <= 0x11FF:  # Hangul (hece + Jamo)
            return ["ko"]
        if 0x4E00 <= code <= 0x9FFF:  # CJK Han (Çince/Japonca ortak)
            has_han = True
    return ["zh", "ja"] if has_han else []


class OpenDictionaryService:
    """
    Anahtar gerektirmeyen içerik sağlayıcı.

    AIService ile aynı arayüzü sunar; WordService ikisini ayırt etmeden çağırır.
    """

    def __init__(self) -> None:
        # Aynı terimin Wiktionary sayfası hem dil algılamada hem her aday dilin
        # üretim denemesinde gerekiyor; sayfayı her seferinde yeniden çekmek,
        # aday sayısı kadar gereksiz ağ gecikmesi ekliyordu. Örnek düzeyinde
        # tutulur: WordService oturum boyu tek örnek kullandığı için paylaşım
        # sağlanır, testlerdeki taze örnekler ise birbirine sızmaz.
        self._page_cache: dict[str, dict | None] = {}

    @property
    def is_configured(self) -> bool:
        """Yapılandırma gerektirmez: her zaman kullanılabilir."""
        return True

    def _fetch_page(self, term: str) -> dict | None:
        """
        Terimin Wiktionary sayfasını çeker ve önbelleğe alır.

        Yazım varyantları sırayla denenir (bkz. _term_variants): Wiktionary
        büyük/küçük harfe ve aksana duyarlı — "Tahanan" 404 verirken "tahanan",
        "Café" 404 verirken "cafe" bulunabiliyor. İlk geçerli yanıtta durulur.
        """
        if term in self._page_cache:
            return self._page_cache[term]

        result: dict | None = None
        for variant in _term_variants(term):
            data = _get_json(WIKTIONARY_API.format(term=urllib.parse.quote(variant)))
            if isinstance(data, dict):
                result = data
                break

        self._page_cache[term] = result
        return result

    def _fetch_wiktionary(self, term: str, language: str) -> dict:
        """
        Wiktionary'den verilen dildeki tanımları çeker.

        Yanıt dil koduna göre gruplanmıştır; yalnızca istenen dilin bölümü alınır.
        """
        data = self._fetch_page(term)
        if data is None:
            return {}

        entries = data.get(language)
        if not entries:
            return {}

        definitions: list[str] = []
        part_of_speech = ""
        for entry in entries:
            if not part_of_speech:
                part_of_speech = entry.get("partOfSpeech", "")
            for d in entry.get("definitions", []):
                text = _strip_html(d.get("definition", ""))
                if text:
                    definitions.append(text)

        return {"definitions": definitions, "part_of_speech": part_of_speech}

    def detect_languages(self, term: str) -> list[str]:
        """
        Kelimenin ait olabileceği dilleri olasılık sırasıyla döndürür.

        Tek bir dil değil liste: tahmin kesin olamaz, çünkü çok dilli kelimeler
        yaygın (ölçüldü — Wiktionary "Baran" için ['en', 'other', 'pl', 'sk',
        'tr'] veriyor; İngilizce'de soyadı, Lehçe'de "koç" demek). Çağıran
        adayları sırayla deneyip ilk tutanı kullanır, ilk tahminde pes etmez.

        Latin dışı alfabeler (Kiril/Hangul/Arap/Kana/Han) ağa çıkmadan kesin
        sinyal verir (bkz. _script_hint): ağ düşse ya da Wiktionary bulamasa bile
        doğru dile düşülür, kör "en" yerine.

        İngilizce Latin kelimelerde başa alınır: hem en olası kullanım, hem de
        telaffuz ve ses veren tek zengin kaynağa (dictionaryapi.dev) bağlanıyor.
        Yanlışsa bedeli yalnızca bir deneme.
        """
        term = term.strip()
        if not term:
            return [RICH_LANGUAGE]

        hint = _script_hint(term)
        data = self._fetch_page(term)
        if data is None:
            # Ağ düştü ya da kayıt yok: betik ipucu varsa kör "en" yerine onu kullan.
            return hint or [RICH_LANGUAGE]

        found = [code for code in data if code in SUPPORTED_LANGUAGES]
        if not found:
            return hint or [RICH_LANGUAGE]

        if hint:
            # Latin dışı kesin sinyal: betik dilleri öne. Wiktionary başka diller
            # de listelese (ör. transliterasyon kaydı) onlar geride kalır.
            found.sort(key=lambda code: hint.index(code) if code in hint else len(hint))
            logger.info("'%s' için dil adayları (betik): %s", term, found)
            return found

        # Latin: İngilizce öne; gerisi Wiktionary sırasında. Kasıtlı olarak
        # kesilmez: sayfa önbelleği sayesinde ek aday ek ağ maliyeti getirmiyor
        # (Gemini'nin ücretli denemelerini WordService sınırlar).
        found.sort(key=lambda code: code != RICH_LANGUAGE)
        logger.info("'%s' için dil adayları: %s", term, found)
        return found

    def detect_language(self, term: str) -> str:
        """En olası tek dili döndürür (bkz. detect_languages)."""
        return self.detect_languages(term)[0]

    def suggest_terms(self, term: str, language: str = "en") -> list[str]:
        """
        Yazımı benzer kelimeleri önerir ("şunu mu demek istediniz?").

        Kelime bulunamadığında kullanılır: girilen metin tam ama yanlış yazılmış
        varsayılır. Yazarken tamamlama için complete_terms kullanın.

        Ağ hatasında boş liste döner: öneri bir kolaylık, kelime ekleme akışını
        bloklamamalı.
        """
        term = term.strip()
        if not term:
            return []

        candidates = _suggest_english(term) if language == RICH_LANGUAGE else []
        if not candidates:
            candidates = _suggest_wiktionary(term)

        suggestions = _pick_suggestions(term, candidates, MIN_SIMILARITY)
        logger.info("'%s' için %d düzeltme önerisi", term, len(suggestions))
        return suggestions

    def complete_terms(self, prefix: str, language: str = "en") -> list[str]:
        """
        Yazılmakta olan kelimeyi tamamlar.

        suggest_terms'ten ayrı bir uç kullanır çünkü işler farklı: burada metin
        yarım, orada tam ama hatalı. Ölçüldü — tek uçla ikisi birden olmuyor:
          • /sug  yarımı tamamlar ("recei" → receive) ama hatayı düzeltmez
            ("recieve" → receive YOK)
          • sp/sl hatayı düzeltir ama yarımda çöp verir ("ephem" → epher, phem)
        """
        prefix = prefix.strip()
        if len(prefix) < MIN_COMPLETION_CHARS:
            return []

        candidates = (
            _complete_english(prefix) if language == RICH_LANGUAGE else _suggest_wiktionary(prefix)
        )
        return _pick_suggestions(prefix, candidates)

    def generate_word_data(self, term: str, language: str = "en") -> dict:
        """
        Açık kaynaklardan kelime içeriği toplar.

        Raises:
            ContentProviderError: Hiçbir kaynaktan tanım bulunamazsa.
        """
        term = term.strip()
        logger.info("Açık sözlükten içerik alınıyor: %s (%s)", term, language)

        if language == RICH_LANGUAGE:
            base = _fetch_english(term)
            if not base.get("definitions"):
                # dictionaryapi.dev argo/az bilinen kelimelerde (örn. "yeet",
                # "rizz") sık sık 404 veriyor; Wiktionary bunları çoğunlukla içerir.
                base = self._fetch_wiktionary(term, RICH_LANGUAGE)
        else:
            base = self._fetch_wiktionary(term, language)

        definitions = base.get("definitions") or []
        if not definitions:
            raise ContentProviderError(
                f"'{term}' için açık sözlüklerde kayıt bulunamadı. "
                "Yazımı kontrol edin ya da Ayarlar'dan Gemini API anahtarı girerek "
                "yapay zekâ ile üretmeyi deneyin."
            )

        short_source = definitions[0]
        long_source = " ".join(definitions[:3])

        # Kaynaklar tanımı İngilizce verir; kullanıcı Türkçe bekliyor.
        short_tr = _translate_to_turkish(short_source)
        long_tr = _translate_to_turkish(long_source) if len(definitions) > 1 else short_tr

        return {
            "definition": long_tr or long_source,
            "definition_short": short_tr or short_source,
            "part_of_speech": base.get("part_of_speech", ""),
            "synonyms": base.get("synonyms", []),
            "antonyms": base.get("antonyms", []),
            "example_sentences": _fetch_examples(term, language),
            "usage_notes": ("" if short_tr else "Bu içerik açık sözlük kaynaklarından derlendi."),
            "phonetic": base.get("phonetic", ""),
            "audio_url": base.get("audio_url", ""),
        }
