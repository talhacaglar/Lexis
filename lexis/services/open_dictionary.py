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

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

from lexis.domain.exceptions import ContentProviderError

logger = logging.getLogger(__name__)

USER_AGENT = "Lexis/0.1 (https://github.com/talhacaglar/lexis)"
TIMEOUT_SECONDS = 12

DICTIONARY_API = "https://api.dictionaryapi.dev/api/v2/entries/en/{term}"
WIKTIONARY_API = "https://en.wiktionary.org/api/rest_v1/page/definition/{term}"
TATOEBA_API = "https://tatoeba.org/en/api_v0/search"
MYMEMORY_API = "https://api.mymemory.translated.net/get"

# dictionaryapi.dev pratikte yalnızca İngilizce sunuyor (diğer dil uçları 404).
RICH_LANGUAGE = "en"

MAX_SYNONYMS = 5
MAX_ANTONYMS = 4
MAX_EXAMPLES = 3

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


def _translate_to_turkish(text: str) -> str:
    """
    İngilizce tanımı Türkçeye çevirir.

    Kaynak daima İngilizce'dir: hem dictionaryapi.dev hem de en.wiktionary,
    kelimenin dili ne olursa olsun tanımları İngilizce verir.

    Başarısızlıkta boş string döner; çeviri alınamasa da kelime eklenebilmeli.
    """
    text = text.strip()
    if not text or len(text) > MAX_TRANSLATE_CHARS:
        return ""

    data = _get_json(MYMEMORY_API, {"q": text, "langpair": "en|tr"})
    if not isinstance(data, dict):
        return ""
    if data.get("responseStatus") != 200:
        return ""
    translated = (data.get("responseData") or {}).get("translatedText") or ""
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


def _fetch_wiktionary(term: str, language: str) -> dict:
    """
    Wiktionary'den verilen dildeki tanımları çeker.

    Yanıt dil koduna göre gruplanmıştır; yalnızca istenen dilin bölümü alınır.
    """
    data = _get_json(WIKTIONARY_API.format(term=urllib.parse.quote(term)))
    if not isinstance(data, dict):
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


class OpenDictionaryService:
    """
    Anahtar gerektirmeyen içerik sağlayıcı.

    AIService ile aynı arayüzü sunar; WordService ikisini ayırt etmeden çağırır.
    """

    @property
    def is_configured(self) -> bool:
        """Yapılandırma gerektirmez: her zaman kullanılabilir."""
        return True

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
        else:
            base = _fetch_wiktionary(term, language)

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
