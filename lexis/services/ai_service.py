"""
Lexis — AI Service

Google Gemini API wrapper. Kelime için zengin içerik üretir.

Yanıt yapısı bir pydantic şema ile (`response_schema`) Gemini'ye dayatılır;
böylece model her zaman aynı alanları ve örnek cümleleri {foreign, turkish}
formatında döndürür. Şema dışı/eski yanıtlar için hoşgörülü bir ayrıştırıcı
yedek olarak kalır.
"""

from __future__ import annotations

import json
import logging
import random
import time

from google import genai
from google.genai import types
from pydantic import BaseModel

from lexis.domain.exceptions import AIServiceError, APIKeyMissingError
from lexis.domain.models import SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.5-flash"

# Ağ isteği zaman aşımı (ms). google-genai http_options bunu ms cinsinden bekler.
REQUEST_TIMEOUT_MS = 30_000

MAX_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 1.0

# Geçici sunucu hataları: bunlarda yeniden denemek anlamlı.
RETRYABLE_STATUS = (429, 500, 502, 503, 504)


def _is_retryable(exc: Exception) -> bool:
    """
    Hatanın geçici olup olmadığını belirler (hız limiti / sunucu / ağ hatası).

    google-genai istisnaları `code` ya da `status_code` taşıyabildiği gibi bazı
    ağ hataları hiçbir kod taşımaz; bu durumda mesaj metnine bakılır.
    """
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if isinstance(code, int) and code in RETRYABLE_STATUS:
        return True
    text = str(exc).lower()
    if any(str(s) in text for s in RETRYABLE_STATUS):
        return True
    return any(
        marker in text
        for marker in ("timeout", "timed out", "temporarily", "unavailable", "connection")
    )


class ExampleSentence(BaseModel):
    """Yabancı dildeki örnek cümle ve Türkçe çevirisi."""

    foreign: str
    turkish: str


class WordData(BaseModel):
    """Gemini'nin bir kelime için üreteceği yapısal içerik."""

    definition: str
    definition_short: str
    part_of_speech: str
    synonyms: list[str]
    antonyms: list[str]
    example_sentences: list[ExampleSentence]
    usage_notes: str = ""


def _build_prompt(term: str, language: str) -> str:
    lang_name = SUPPORTED_LANGUAGES.get(language, language)
    return f"""Sen bir dil öğrenme asistanısın. Türkçe konuşan birinin {lang_name} öğrenmesine yardım ediyorsun.

Verilen kelime: "{term}" ({lang_name})

Lütfen aşağıdaki bilgileri üret:

1. definition: Kelimenin ayrıntılı Türkçe tanımı (2-4 cümle).
2. definition_short: Tek cümlelik kısa Türkçe tanım.
3. part_of_speech: Sözcük türü Türkçe olarak (İsim, Fiil, Sıfat, Zarf vs.)
4. synonyms: 3-5 adet {lang_name} eş anlamlı kelime.
5. antonyms: 2-4 adet {lang_name} zıt anlamlı kelime.
6. example_sentences: Tam olarak 3 adet örnek. Her örnek "foreign" ({lang_name} cümle)
   ve "turkish" (Türkçe çevirisi) alanlarını içermelidir.
7. usage_notes: Türkçe kısa kullanım notu.

Yanıtını verilen JSON şemasına birebir uyacak şekilde ver."""


def _format_examples(raw: object) -> list[str]:
    """
    Örnek cümleleri uygulamanın beklediği 'foreign\\nturkish' string listesine
    dönüştürür. Hem yapısal (dict / pydantic) hem de eski düz-string yanıtlarına
    karşı toleranslıdır.
    """
    formatted: list[str] = []
    flat: list[str] = []

    for ex in raw or []:
        if isinstance(ex, ExampleSentence):
            foreign, turkish = ex.foreign, ex.turkish
        elif isinstance(ex, dict):
            foreign, turkish = ex.get("foreign", ""), ex.get("turkish", "")
        else:
            s = str(ex).strip()
            (formatted if "\n" in s else flat).append(s)
            continue

        if foreign and turkish:
            formatted.append(f"{foreign}\n{turkish}")
        elif foreign:
            formatted.append(foreign)

    # Eski format: düz string'ler çift hâlinde (yabancı, türkçe) gelmiş olabilir.
    if not formatted and flat:
        if len(flat) >= 4 and len(flat) % 2 == 0:
            formatted = [f"{flat[i]}\n{flat[i + 1]}" for i in range(0, len(flat), 2)]
        else:
            formatted = flat

    return formatted


def _check_blocked(response) -> None:
    """
    Yanıtın güvenlik filtresine ya da uzunluk sınırına takılıp takılmadığını denetler.

    Bloklanan yanıtta `text` boş gelir; bu denetim olmadan kullanıcı "AI yanıtı
    ayrıştırılamadı" gibi nedeni gizleyen bir hata görürdü.
    """
    feedback = getattr(response, "prompt_feedback", None)
    block_reason = getattr(feedback, "block_reason", None) if feedback else None
    if block_reason:
        raise AIServiceError(
            f"İstek güvenlik filtresine takıldı ({block_reason}). Farklı bir kelime deneyin."
        )

    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        raise AIServiceError("Model boş yanıt döndürdü. Lütfen tekrar deneyin.")

    finish_reason = getattr(candidates[0], "finish_reason", None)
    if finish_reason is None:
        return

    reason = getattr(finish_reason, "name", str(finish_reason)).upper()
    if reason in ("SAFETY", "PROHIBITED_CONTENT", "BLOCKLIST", "RECITATION"):
        raise AIServiceError(
            f"Yanıt güvenlik filtresine takıldı ({reason}). Farklı bir kelime deneyin."
        )
    if reason == "MAX_TOKENS":
        raise AIServiceError("Yanıt uzunluk sınırına takıldı. Lütfen tekrar deneyin.")


class AIService:
    """Google Gemini API ile kelime içeriği üretir."""

    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL) -> None:
        self._api_key = api_key
        self._model = model
        self._client = None
        if api_key:
            self._setup(api_key)

    def _setup(self, api_key: str) -> None:
        try:
            # Zaman aşımı olmadan asılı kalan bir istek worker thread'ini süresiz bloklar.
            self._client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS),
            )
            self._api_key = api_key
            logger.info("Gemini API yapılandırıldı (model: %s).", self._model)
        except Exception as e:
            logger.error(f"Gemini API yapılandırma hatası: {e}")
            raise AIServiceError("API yapılandırılamadı.", original=e) from e

    def configure(self, api_key: str) -> None:
        """API anahtarını runtime'da güncelle."""
        self._setup(api_key)

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    def generate_word_data(self, term: str, language: str = "en") -> dict:
        """
        Verilen kelime için zengin içerik üretir.

        Returns:
            dict: definition, definition_short, part_of_speech, synonyms,
            antonyms, example_sentences (list[str]), usage_notes.

        Raises:
            APIKeyMissingError: API anahtarı yoksa.
            AIServiceError: Üretim başarısızsa.
        """
        if not self.is_configured:
            raise APIKeyMissingError()

        prompt = _build_prompt(term, language)
        logger.info(f"Kelime içeriği üretiliyor: {term} ({language})")

        try:
            response = self._generate_with_retry(prompt)
            _check_blocked(response)

            # Tercihen SDK'nın doğrulanmış nesnesini kullan; yoksa metni ayrıştır.
            parsed: WordData | None = getattr(response, "parsed", None)
            if isinstance(parsed, WordData):
                data = parsed
            else:
                data = WordData.model_validate(json.loads(response.text))

            return {
                "definition": data.definition,
                "definition_short": data.definition_short,
                "part_of_speech": data.part_of_speech,
                "synonyms": data.synonyms,
                "antonyms": data.antonyms,
                "example_sentences": _format_examples(data.example_sentences),
                "usage_notes": data.usage_notes,
            }
        except json.JSONDecodeError as e:
            logger.error(f"AI yanıtı JSON parse hatası: {e}")
            raise AIServiceError("AI yanıtı ayrıştırılamadı.", original=e) from e
        except (APIKeyMissingError, AIServiceError):
            raise
        except Exception as e:
            logger.error(f"Gemini API hatası: {e}")
            raise AIServiceError(str(e), original=e) from e

    def _generate_with_retry(self, prompt: str):
        """
        generate_content'i çağırır; geçici hatalarda üstel geri çekilmeyle yeniden dener.

        Kalıcı hatalar (geçersiz anahtar, kota bitmiş vb.) ilk denemede yükseltilir —
        yeniden denemek yalnızca kullanıcıyı bekletir.
        """
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=WordData,
        )

        last_error: Exception | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                return self._client.models.generate_content(
                    model=self._model, contents=prompt, config=config
                )
            except Exception as e:
                last_error = e
                if attempt == MAX_ATTEMPTS or not _is_retryable(e):
                    raise
                # Jitter, eşzamanlı isteklerin aynı anda tekrar denemesini önler.
                delay = BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)) + random.uniform(0, 0.3)
                logger.warning(
                    "Gemini isteği geçici hata verdi (deneme %d/%d), %.1f sn sonra tekrar: %s",
                    attempt,
                    MAX_ATTEMPTS,
                    delay,
                    e,
                )
                time.sleep(delay)

        raise AIServiceError(str(last_error), original=last_error)  # pragma: no cover
