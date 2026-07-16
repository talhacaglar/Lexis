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

from google import genai
from google.genai import types
from pydantic import BaseModel

from lexis.domain.exceptions import AIServiceError, APIKeyMissingError
from lexis.domain.models import SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.5-flash"


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
            self._client = genai.Client(api_key=api_key)
            self._api_key = api_key
            logger.info("Gemini API yapılandırıldı.")
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
            response = self._client.models.generate_content(
                model=self._model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=WordData,
                ),
            )

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
