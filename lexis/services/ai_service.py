"""
Lexis — AI Service

Google Gemini API wrapper. Kelime için zengin içerik üretir.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from google import genai
from google.genai import types

from lexis.domain.exceptions import AIServiceError, APIKeyMissingError
from lexis.domain.models import SUPPORTED_LANGUAGES

logger = logging.getLogger(__name__)

# Gemini'den beklenen JSON şeması
WORD_DATA_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "definition": {"type": "STRING"},
        "definition_short": {"type": "STRING"},
        "part_of_speech": {"type": "STRING"},
        "synonyms": {"type": "ARRAY", "items": {"type": "STRING"}},
        "antonyms": {"type": "ARRAY", "items": {"type": "STRING"}},
        "example_sentences": {"type": "ARRAY", "items": {"type": "STRING"}},
        "usage_notes": {"type": "STRING"},
    },
    "required": ["definition", "definition_short", "part_of_speech", "synonyms", "antonyms", "example_sentences"],
}


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
6. example_sentences: DİKKAT: Tam olarak 3 adet {lang_name} örnek cümle. Bu 3 cümlenin HER BİRİ JSON dizisinin (array) içinde ayrı bir OBJE (object) olmalıdır. Objenin iki alanı olmalıdır: "foreign" (yabancı cümle) ve "turkish" (Türkçe çevirisi). ÖRNEK: [{{"foreign": "I love apples.", "turkish": "Elma severim."}}]
7. usage_notes: Türkçe kullanım notu.

Yanıtını JSON formatında ver."""


class AIService:
    """Google Gemini API ile kelime içeriği üretir."""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self._api_key = api_key
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
            dict: definition, definition_short, part_of_speech...

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
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                )
            )
            data = json.loads(response.text)

            examples_raw = data.get("example_sentences", [])
            examples_formatted = []
            flat_strings = []

            for ex in examples_raw:
                if isinstance(ex, dict):
                    foreign = ex.get("foreign", "")
                    turkish = ex.get("turkish", "")
                    if foreign and turkish:
                        examples_formatted.append(f"{foreign}\n{turkish}")
                    elif foreign:
                        examples_formatted.append(foreign)
                else:
                    s = str(ex).strip()
                    if "\n" in s:
                        examples_formatted.append(s)
                    else:
                        flat_strings.append(s)

            if not examples_formatted and flat_strings:
                if len(flat_strings) % 2 == 0 and len(flat_strings) >= 4:
                    for i in range(0, len(flat_strings), 2):
                        examples_formatted.append(f"{flat_strings[i]}\n{flat_strings[i+1]}")
                else:
                    examples_formatted = flat_strings

            # Eksik alanları varsayılanlarla doldur
            return {
                "definition": data.get("definition", ""),
                "definition_short": data.get("definition_short", ""),
                "part_of_speech": data.get("part_of_speech", ""),
                "synonyms": data.get("synonyms", []),
                "antonyms": data.get("antonyms", []),
                "example_sentences": examples_formatted,
                "usage_notes": data.get("usage_notes", ""),
            }
        except json.JSONDecodeError as e:
            logger.error(f"AI yanıtı JSON parse hatası: {e}")
            raise AIServiceError("AI yanıtı ayrıştırılamadı.", original=e) from e
        except Exception as e:
            logger.error(f"Gemini API hatası: {e}")
            raise AIServiceError(str(e), original=e) from e
