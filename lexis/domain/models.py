"""
Lexis — Domain Models

Bu modül uygulamanın çekirdek veri modellerini içerir.
Herhangi bir framework veya veritabanı bağımlılığı yoktur.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum


def utcnow() -> datetime:
    """Timezone-aware (UTC) şu anki zaman. datetime.utcnow() yerine kullanılır."""
    return datetime.now(timezone.utc)


class ReviewGrade(int, Enum):
    """
    Bir tekrar oturumunda kullanıcının verdiği değerlendirme.
    Değer, SM-2 algoritmasındaki 'quality' (0-5) puanına karşılık gelir.
    """
    AGAIN = 1   # Hatırlanamadı
    HARD = 3    # Zorlanarak hatırlandı
    GOOD = 4    # Hatırlandı
    EASY = 5    # Kolayca hatırlandı

    @property
    def display_name(self) -> str:
        return {1: "Tekrar", 3: "Zor", 4: "İyi", 5: "Kolay"}[self.value]

    @property
    def color(self) -> str:
        return {1: "#EF4444", 3: "#F59E0B", 4: "#4ADE80", 5: "#60A5FA"}[self.value]


# Hatırlanamayan kart, gün sonrasına atılmak yerine bu kadar dakika sonra
# aynı oturum içinde yeniden sorulur.
RELEARN_DELAY_MINUTES = 10

# "Zor" değerlendirmesinde aralık, tam ease çarpanı yerine bu katsayıyla büyür.
HARD_INTERVAL_FACTOR = 1.2

# Bir kelimenin "öğrenildi" sayılması için gereken aralık eşiği (gün).
LEARNED_INTERVAL_DAYS = 21


def compute_sm2(
    ease_factor: float,
    interval_days: int,
    repetitions: int,
    quality: int,
) -> tuple[float, int, int, int]:
    """
    SM-2 aralıklı tekrar algoritması (saf fonksiyon).

    Returns:
        (yeni ease_factor, yeni interval_days, yeni repetitions, delay_minutes)

        delay_minutes > 0 ise kart gün yerine dakika sonrasına planlanmalıdır
        (oturum içi yeniden gösterim); 0 ise interval_days geçerlidir.
    """
    previous_interval = interval_days
    delay_minutes = 0

    if quality < 3:
        # Hatırlanamadı: ilerleme sıfırlanır ve kart aynı oturumda geri gelir.
        repetitions = 0
        interval_days = 0
        delay_minutes = RELEARN_DELAY_MINUTES
    else:
        if repetitions == 0:
            interval_days = 1
        elif repetitions == 1:
            interval_days = 6
        elif quality == ReviewGrade.HARD:
            # Zorlanarak hatırlandı: aralık büyür ama tam ease kadar değil.
            interval_days = max(1, round(previous_interval * HARD_INTERVAL_FACTOR))
        else:
            interval_days = max(1, round(previous_interval * ease_factor))
        repetitions += 1

    ease_factor += 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    ease_factor = max(1.3, ease_factor)

    return ease_factor, interval_days, repetitions, delay_minutes


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
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)
    last_reviewed_at: datetime | None = None
    review_count: int = 0
    # ── Aralıklı tekrar (SM-2) ──
    ease_factor: float = 2.5
    interval_days: int = 0
    repetitions: int = 0
    due_at: datetime | None = None
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
        self.last_reviewed_at = utcnow()
        self.review_count += 1
        self.updated_at = utcnow()

    @property
    def is_due(self) -> bool:
        """Kelimenin tekrar zamanı geldi mi? (Hiç çalışılmamışlar da dahildir.)"""
        if self.due_at is None:
            return True
        return self.due_at <= utcnow()

    def apply_review(self, grade: ReviewGrade) -> None:
        """
        Bir tekrar değerlendirmesini uygular: SM-2 ile yeni aralığı hesaplar,
        sonraki tekrar tarihini (due_at) belirler ve öğrenme durumunu günceller.
        """
        self.ease_factor, self.interval_days, self.repetitions, delay_minutes = compute_sm2(
            self.ease_factor, self.interval_days, self.repetitions, int(grade)
        )
        now = utcnow()
        if delay_minutes:
            self.due_at = now + timedelta(minutes=delay_minutes)
        else:
            self.due_at = now + timedelta(days=self.interval_days)

        if grade == ReviewGrade.AGAIN:
            self.status = WordStatus.NEEDS_REVIEW
        elif self.repetitions >= 3 and self.interval_days >= LEARNED_INTERVAL_DAYS:
            # Olgunluk aralıkla ölçülür: tek bir "Zor" değerlendirmesi ease'i
            # düşürüp durumu kalıcı olarak kilitlemesin.
            self.status = WordStatus.LEARNED
        else:
            self.status = WordStatus.LEARNING

        self.mark_reviewed()

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
            "ease_factor": self.ease_factor,
            "interval_days": self.interval_days,
            "repetitions": self.repetitions,
            "due_at": self.due_at.isoformat() if self.due_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Word:
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
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else utcnow(),
            last_reviewed_at=datetime.fromisoformat(data["last_reviewed_at"]) if data.get("last_reviewed_at") else None,
            review_count=data.get("review_count", 0),
            ease_factor=data.get("ease_factor", 2.5),
            interval_days=data.get("interval_days", 0),
            repetitions=data.get("repetitions", 0),
            due_at=datetime.fromisoformat(data["due_at"]) if data.get("due_at") else None,
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
    # Zamanı gelmiş planlı tekrarlar (hiç çalışılmamışlar hariç).
    due_today: int = 0
    # Hiç çalışılmamış, dolayısıyla henüz planlanmamış kelimeler.
    unreviewed: int = 0

    @property
    def practice_queue_size(self) -> int:
        """Çalışma kuyruğunun toplam boyutu: planlı tekrarlar + hiç çalışılmamışlar."""
        return self.due_today + self.unreviewed
