"""
Lexis — Domain Models

Bu modül uygulamanın çekirdek veri modellerini içerir.
Herhangi bir framework veya veritabanı bağımlılığı yoktur.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class WordStatus(str, Enum):
    """Kelimenin öğrenme durumu."""
    NEW = "new"
    LEARNING = "learning"
    LEARNED = "learned"
    NEEDS_REVIEW = "needs_review"

    @property
    def display_name(self) -> str:
        return {
            "new": "Yeni",
            "learning": "Öğreniyorum",
            "learned": "Öğrendim",
            "needs_review": "Tekrar Gerek",
        }[self.value]

    @property
    def color(self) -> str:
        return {
            "new": "#6C63FF",
            "learning": "#F59E0B",
            "learned": "#4ADE80",
            "needs_review": "#EF4444",
        }[self.value]

    @property
    def icon(self) -> str:
        return {
            "new": "✦",
            "learning": "◐",
            "learned": "✓",
            "needs_review": "↺",
        }[self.value]


SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "İngilizce",
    "de": "Almanca",
    "fr": "Fransızca",
    "es": "İspanyolca",
    "it": "İtalyanca",
    "pt": "Portekizce",
    "ja": "Japonca",
    "zh": "Çince",
    "ko": "Korece",
    "ar": "Arapça",
    "ru": "Rusça",
    "nl": "Hollandaca",
    "pl": "Lehçe",
    "sv": "İsveççe",
}


@dataclass
class Word:
    """
    Bir kelimeyi temsil eden domain modeli.
    Tüm liste alanları Python list olarak saklanır;
    veritabanına yazılırken JSON string'e dönüştürülür.
    """
    term: str
    language: str = "en"
    definition: str = ""
    definition_short: str = ""
    synonyms: list[str] = field(default_factory=list)
    antonyms: list[str] = field(default_factory=list)
    example_sentences: list[str] = field(default_factory=list)
    usage_notes: str = ""
    part_of_speech: str = ""
    status: WordStatus = WordStatus.NEW
    is_favorite: bool = False
    tags: list[str] = field(default_factory=list)
    ai_generated: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_reviewed_at: Optional[datetime] = None
    review_count: int = 0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def language_display(self) -> str:
        return SUPPORTED_LANGUAGES.get(self.language, self.language.upper())

    @property
    def status_display(self) -> str:
        return self.status.display_name

    @property
    def synonyms_text(self) -> str:
        return ", ".join(self.synonyms)

    @property
    def antonyms_text(self) -> str:
        return ", ".join(self.antonyms)

    def mark_reviewed(self) -> None:
        self.last_reviewed_at = datetime.utcnow()
        self.review_count += 1
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> dict:
        """Export için dict dönüşümü."""
        return {
            "id": self.id,
            "term": self.term,
            "language": self.language,
            "definition": self.definition,
            "definition_short": self.definition_short,
            "synonyms": self.synonyms,
            "antonyms": self.antonyms,
            "example_sentences": self.example_sentences,
            "usage_notes": self.usage_notes,
            "part_of_speech": self.part_of_speech,
            "status": self.status.value,
            "is_favorite": self.is_favorite,
            "tags": self.tags,
            "ai_generated": self.ai_generated,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_reviewed_at": self.last_reviewed_at.isoformat() if self.last_reviewed_at else None,
            "review_count": self.review_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Word":
        """Dict'ten Word oluşturma (import için)."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            term=data["term"],
            language=data.get("language", "en"),
            definition=data.get("definition", ""),
            definition_short=data.get("definition_short", ""),
            synonyms=data.get("synonyms", []),
            antonyms=data.get("antonyms", []),
            example_sentences=data.get("example_sentences", []),
            usage_notes=data.get("usage_notes", ""),
            part_of_speech=data.get("part_of_speech", ""),
            status=WordStatus(data.get("status", "new")),
            is_favorite=data.get("is_favorite", False),
            tags=data.get("tags", []),
            ai_generated=data.get("ai_generated", False),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.utcnow(),
            last_reviewed_at=datetime.fromisoformat(data["last_reviewed_at"]) if data.get("last_reviewed_at") else None,
            review_count=data.get("review_count", 0),
        )


@dataclass
class WordStats:
    """Sözlük istatistikleri."""
    total: int = 0
    new: int = 0
    learning: int = 0
    learned: int = 0
    needs_review: int = 0
    favorites: int = 0
    added_today: int = 0
    reviewed_today: int = 0
