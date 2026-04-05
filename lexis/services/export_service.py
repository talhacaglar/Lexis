"""
Lexis — Export / Import Service

JSON ve CSV formatında kelime dışa ve içe aktarma.
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

from lexis.domain.exceptions import ExportError
from lexis.domain.exceptions import ImportError as LexisImportError
from lexis.domain.models import Word
from lexis.persistence.word_repository import WordRepository

logger = logging.getLogger(__name__)


class ExportService:
    """JSON ve CSV import/export işlemleri."""

    def __init__(self, repository: WordRepository) -> None:
        self._repo = repository

    # ── JSON ──────────────────────────────────────────────────────────────

    def export_json(self, path: Path) -> int:
        """Tüm kelimeleri JSON dosyasına aktarır. Aktarılan sayıyı döndürür."""
        try:
            words = self._repo.get_all()
            data = {
                "version": "1.0",
                "app": "lexis",
                "count": len(words),
                "words": [w.to_dict() for w in words],
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"JSON dışa aktarıldı: {path} ({len(words)} kelime)")
            return len(words)
        except Exception as e:
            raise ExportError(f"JSON dışa aktarma hatası: {e}") from e

    def import_json(self, path: Path, skip_duplicates: bool = True) -> tuple[int, int]:
        """
        JSON dosyasından kelime içe aktarır.

        Returns:
            (imported_count, skipped_count) tuple
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            words_data = data.get("words", data) if isinstance(data, dict) else data
            if not isinstance(words_data, list):
                raise LexisImportError("Geçersiz JSON formatı.")

            imported = 0
            skipped = 0

            for word_data in words_data:
                try:
                    word = Word.from_dict(word_data)
                    if skip_duplicates and self._repo.exists(word.term, word.language):
                        skipped += 1
                        continue
                    self._repo.create(word)
                    imported += 1
                except Exception as e:
                    logger.warning(f"Kelime içe aktarılamadı: {word_data.get('term', '?')} — {e}")
                    skipped += 1

            logger.info(f"JSON içe aktarıldı: {imported} kelime, {skipped} atlandı")
            return imported, skipped

        except LexisImportError:
            raise
        except Exception as e:
            raise LexisImportError(f"JSON içe aktarma hatası: {e}") from e

    # ── CSV ───────────────────────────────────────────────────────────────

    CSV_FIELDS = [
        "term", "language", "definition_short", "definition",
        "part_of_speech", "synonyms", "antonyms",
        "example_sentences", "usage_notes", "status",
        "is_favorite", "tags", "created_at",
    ]

    def export_csv(self, path: Path) -> int:
        """Tüm kelimeleri CSV dosyasına aktarır."""
        try:
            words = self._repo.get_all()
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.CSV_FIELDS)
                writer.writeheader()
                for w in words:
                    d = w.to_dict()
                    writer.writerow({
                        "term": d["term"],
                        "language": d["language"],
                        "definition_short": d["definition_short"],
                        "definition": d["definition"],
                        "part_of_speech": d["part_of_speech"],
                        "synonyms": ", ".join(d["synonyms"]),
                        "antonyms": ", ".join(d["antonyms"]),
                        "example_sentences": " | ".join(d["example_sentences"]),
                        "usage_notes": d["usage_notes"],
                        "status": d["status"],
                        "is_favorite": "evet" if d["is_favorite"] else "hayır",
                        "tags": ", ".join(d["tags"]),
                        "created_at": d["created_at"][:10],
                    })
            logger.info(f"CSV dışa aktarıldı: {path} ({len(words)} kelime)")
            return len(words)
        except Exception as e:
            raise ExportError(f"CSV dışa aktarma hatası: {e}") from e

    def import_csv(self, path: Path, skip_duplicates: bool = True) -> tuple[int, int]:
        """CSV dosyasından kelime içe aktarır."""
        try:
            imported = 0
            skipped = 0

            with open(path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        term = row.get("term", "").strip()
                        language = row.get("language", "en").strip()
                        if not term:
                            skipped += 1
                            continue

                        if skip_duplicates and self._repo.exists(term, language):
                            skipped += 1
                            continue

                        synonyms = [s.strip() for s in row.get("synonyms", "").split(",") if s.strip()]
                        antonyms = [a.strip() for a in row.get("antonyms", "").split(",") if a.strip()]
                        examples = [e.strip() for e in row.get("example_sentences", "").split("|") if e.strip()]
                        tags = [t.strip() for t in row.get("tags", "").split(",") if t.strip()]

                        word = Word(
                            term=term,
                            language=language,
                            definition=row.get("definition", ""),
                            definition_short=row.get("definition_short", ""),
                            part_of_speech=row.get("part_of_speech", ""),
                            synonyms=synonyms,
                            antonyms=antonyms,
                            example_sentences=examples,
                            usage_notes=row.get("usage_notes", ""),
                            tags=tags,
                            ai_generated=False,
                        )
                        self._repo.create(word)
                        imported += 1
                    except Exception as e:
                        logger.warning(f"CSV satırı içe aktarılamadı: {row.get('term', '?')} — {e}")
                        skipped += 1

            logger.info(f"CSV içe aktarıldı: {imported} kelime, {skipped} atlandı")
            return imported, skipped

        except LexisImportError:
            raise
        except Exception as e:
            raise LexisImportError(f"CSV içe aktarma hatası: {e}") from e
