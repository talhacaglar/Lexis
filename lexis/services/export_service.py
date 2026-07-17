"""
Lexis — Export / Import Service

JSON ve CSV formatında kelime dışa ve içe aktarma.
"""

from __future__ import annotations

import csv
import json
import logging
import os
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import IO

from lexis.domain.exceptions import ExportError, LexisImportError
from lexis.domain.models import Word
from lexis.persistence.word_repository import WordRepository

logger = logging.getLogger(__name__)


@contextmanager
def _atomic_write(path: Path, encoding: str, newline: str | None = None) -> Iterator[IO]:
    """
    Aynı dizinde geçici dosyaya yazıp os.replace ile hedefe taşır.

    Yazma sırasında bir hata olursa kullanıcının mevcut dosyası bozulmadan/yarım
    kalmadan yerinde durur; taşıma aynı dosya sistemi içinde atomiktir.
    """
    path = Path(path)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        with open(tmp_path, "w", encoding=encoding, newline=newline) as f:
            yield f
        os.replace(tmp_path, path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


class ExportService:
    """JSON ve CSV import/export işlemleri."""

    def __init__(self, repository: WordRepository) -> None:
        self._repo = repository

    def _collect(
        self,
        rows: list,
        build: Callable[[object], Word | None],
        skip_duplicates: bool,
    ) -> tuple[list[Word], int]:
        """
        Ham satırları Word listesine dönüştürür; bozuk satırları atlar.

        Mükerrer kontrolü hem veritabanına hem de aynı dosyanın daha önceki
        satırlarına karşı yapılır (toplu yazımda DB henüz o satırları görmez).
        """
        words: list[Word] = []
        seen: set[tuple[str, str]] = set()
        skipped = 0

        for row in rows:
            try:
                word = build(row)
                if word is None:
                    skipped += 1
                    continue
                key = (word.term.strip().casefold(), word.language)
                if skip_duplicates and (key in seen or self._repo.exists(word.term, word.language)):
                    skipped += 1
                    continue
                seen.add(key)
                words.append(word)
            except Exception as e:
                logger.warning(f"Satır içe aktarılamadı — {e}")
                skipped += 1

        return words, skipped

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
            with _atomic_write(path, encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"JSON dışa aktarıldı: {path} ({len(words)} kelime)")
            return len(words)
        except Exception as e:
            raise ExportError(f"JSON dışa aktarma hatası: {e}") from e

    def import_json(self, path: Path, skip_duplicates: bool = True) -> tuple[int, int]:
        """
        JSON dosyasından kelime içe aktarır.

        Bozuk satırlar atlanır; geçerli olanların tamamı tek transaction'da
        yazılır (ya hepsi ya hiçbiri).

        Returns:
            (imported_count, skipped_count) tuple
        """
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            words_data = data.get("words", data) if isinstance(data, dict) else data
            if not isinstance(words_data, list):
                raise LexisImportError("Geçersiz JSON formatı.")

            words, skipped = self._collect(words_data, Word.from_dict, skip_duplicates)
            imported = self._repo.create_many(words)

            logger.info(f"JSON içe aktarıldı: {imported} kelime, {skipped} atlandı")
            return imported, skipped

        except LexisImportError:
            raise
        except Exception as e:
            raise LexisImportError(f"JSON içe aktarma hatası: {e}") from e

    # ── CSV ───────────────────────────────────────────────────────────────

    CSV_FIELDS = [
        "term",
        "language",
        "definition_short",
        "definition",
        "part_of_speech",
        "synonyms",
        "antonyms",
        "example_sentences",
        "usage_notes",
        "status",
        "is_favorite",
        "tags",
        "created_at",
    ]

    def export_csv(self, path: Path) -> int:
        """Tüm kelimeleri CSV dosyasına aktarır."""
        try:
            words = self._repo.get_all()
            with _atomic_write(path, encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=self.CSV_FIELDS)
                writer.writeheader()
                for w in words:
                    d = w.to_dict()
                    writer.writerow(
                        {
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
                        }
                    )
            logger.info(f"CSV dışa aktarıldı: {path} ({len(words)} kelime)")
            return len(words)
        except Exception as e:
            raise ExportError(f"CSV dışa aktarma hatası: {e}") from e

    @staticmethod
    def _word_from_csv_row(row: dict) -> Word | None:
        """Bir CSV satırını Word'e çevirir; terim yoksa None döndürür (atlanır)."""
        term = (row.get("term") or "").strip()
        if not term:
            return None

        def split_list(field: str, sep: str = ",") -> list[str]:
            return [p.strip() for p in (row.get(field) or "").split(sep) if p.strip()]

        return Word(
            term=term,
            language=(row.get("language") or "en").strip(),
            definition=row.get("definition", ""),
            definition_short=row.get("definition_short", ""),
            part_of_speech=row.get("part_of_speech", ""),
            synonyms=split_list("synonyms"),
            antonyms=split_list("antonyms"),
            example_sentences=split_list("example_sentences", "|"),
            usage_notes=row.get("usage_notes", ""),
            tags=split_list("tags"),
            ai_generated=False,
        )

    def import_csv(self, path: Path, skip_duplicates: bool = True) -> tuple[int, int]:
        """
        CSV dosyasından kelime içe aktarır.

        Bozuk satırlar atlanır; geçerli olanların tamamı tek transaction'da yazılır.
        """
        try:
            with open(path, encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f))

            words, skipped = self._collect(rows, self._word_from_csv_row, skip_duplicates)
            imported = self._repo.create_many(words)

            logger.info(f"CSV içe aktarıldı: {imported} kelime, {skipped} atlandı")
            return imported, skipped

        except LexisImportError:
            raise
        except Exception as e:
            raise LexisImportError(f"CSV içe aktarma hatası: {e}") from e
