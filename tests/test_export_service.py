"""
Lexis — Tests: Dışa / içe aktarma (JSON, CSV)
"""

import csv
import json

import pytest

from lexis.domain.exceptions import ExportError, LexisImportError
from lexis.domain.models import Word
from lexis.persistence.word_repository import WordRepository
from lexis.services.export_service import ExportService

# ── JSON export ───────────────────────────────────────────────────────────


def test_export_json_writes_all_words(
    export_service: ExportService, repo: WordRepository, tmp_path, sample_word: Word
):
    repo.create(sample_word)
    target = tmp_path / "out.json"

    count = export_service.export_json(target)

    assert count == 1
    data = json.loads(target.read_text(encoding="utf-8"))
    assert data["app"] == "lexis"
    assert data["count"] == 1
    assert data["words"][0]["term"] == "ephemeral"
    assert data["words"][0]["synonyms"] == ["transient", "fleeting", "momentary"]


def test_export_json_leaves_no_temp_files(
    export_service: ExportService, repo: WordRepository, tmp_path, sample_word: Word
):
    repo.create(sample_word)
    target = tmp_path / "out.json"

    export_service.export_json(target)

    assert target.exists()
    assert list(tmp_path.glob("*.tmp")) == []


def test_export_json_keeps_existing_file_intact_on_failure(
    export_service: ExportService, tmp_path, monkeypatch
):
    """Yazma hata verirse kullanıcının mevcut dosyası bozulmamalı."""
    target = tmp_path / "out.json"
    target.write_text("ÖNCEKİ İÇERİK", encoding="utf-8")

    def boom(*args, **kwargs):
        raise OSError("disk dolu")

    monkeypatch.setattr(json, "dump", boom)

    with pytest.raises(ExportError):
        export_service.export_json(target)

    assert target.read_text(encoding="utf-8") == "ÖNCEKİ İÇERİK"
    assert list(tmp_path.glob("*.tmp")) == []  # geçici dosya temizlenmiş


# ── JSON import ───────────────────────────────────────────────────────────


def test_import_json_round_trip(
    export_service: ExportService, repo: WordRepository, tmp_path, sample_word: Word
):
    repo.create(sample_word)
    target = tmp_path / "out.json"
    export_service.export_json(target)
    repo.delete_all()

    imported, skipped = export_service.import_json(target)

    assert (imported, skipped) == (1, 0)
    restored = repo.get_all()[0]
    assert restored.term == "ephemeral"
    assert restored.tags == ["vocabulary", "adjective"]
    assert restored.example_sentences == sample_word.example_sentences


def test_import_json_accepts_bare_list(
    export_service: ExportService, repo: WordRepository, tmp_path
):
    target = tmp_path / "bare.json"
    target.write_text(json.dumps([{"term": "solitude", "language": "en"}]), encoding="utf-8")

    imported, skipped = export_service.import_json(target)

    assert (imported, skipped) == (1, 0)
    assert repo.get_all()[0].term == "solitude"


def test_import_json_skips_duplicates_already_in_db(
    export_service: ExportService, repo: WordRepository, tmp_path, sample_word: Word
):
    repo.create(sample_word)
    target = tmp_path / "dup.json"
    target.write_text(json.dumps([{"term": "ephemeral", "language": "en"}]), encoding="utf-8")

    imported, skipped = export_service.import_json(target)

    assert (imported, skipped) == (0, 1)
    assert len(repo.get_all()) == 1


def test_import_json_skips_duplicates_within_same_file(
    export_service: ExportService, repo: WordRepository, tmp_path
):
    """Aynı dosyada tekrarlanan kelime bir kez alınmalı (toplu yazımda DB henüz görmez)."""
    target = tmp_path / "dup.json"
    target.write_text(
        json.dumps(
            [
                {"term": "candid", "language": "en"},
                {"term": "Candid", "language": "en"},  # yalnızca harf büyüklüğü farklı
            ]
        ),
        encoding="utf-8",
    )

    imported, skipped = export_service.import_json(target)

    assert (imported, skipped) == (1, 1)
    assert len(repo.get_all()) == 1


def test_import_json_skips_malformed_rows_but_keeps_valid_ones(
    export_service: ExportService, repo: WordRepository, tmp_path
):
    target = tmp_path / "mixed.json"
    target.write_text(
        json.dumps(
            [
                {"term": "valid", "language": "en"},
                {"language": "en"},  # term yok → bozuk
                {"term": "also_valid", "language": "en"},
            ]
        ),
        encoding="utf-8",
    )

    imported, skipped = export_service.import_json(target)

    assert (imported, skipped) == (2, 1)
    assert {w.term for w in repo.get_all()} == {"valid", "also_valid"}


def test_import_json_rejects_invalid_format(export_service: ExportService, tmp_path):
    target = tmp_path / "bad.json"
    target.write_text(json.dumps({"words": "bu bir liste değil"}), encoding="utf-8")

    with pytest.raises(LexisImportError):
        export_service.import_json(target)


def test_import_json_rejects_unparsable_file(export_service: ExportService, tmp_path):
    target = tmp_path / "broken.json"
    target.write_text("{ bu JSON değil", encoding="utf-8")

    with pytest.raises(LexisImportError):
        export_service.import_json(target)


def test_import_json_is_atomic_when_write_fails(
    export_service: ExportService, repo: WordRepository, tmp_path, monkeypatch
):
    """Toplu yazım ortasında hata olursa hiçbir kelime kalmamalı."""
    target = tmp_path / "many.json"
    target.write_text(
        json.dumps([{"term": f"w{i}", "language": "en"} for i in range(5)]),
        encoding="utf-8",
    )

    def boom(*args, **kwargs):
        raise RuntimeError("yazma hatası")

    monkeypatch.setattr(repo, "create_many", boom)

    with pytest.raises(LexisImportError):
        export_service.import_json(target)

    assert repo.get_all() == []


# ── CSV ───────────────────────────────────────────────────────────────────


def test_export_csv_flattens_list_fields(
    export_service: ExportService, repo: WordRepository, tmp_path, sample_word: Word
):
    repo.create(sample_word)
    target = tmp_path / "out.csv"

    count = export_service.export_csv(target)

    assert count == 1
    with open(target, encoding="utf-8-sig") as f:
        row = next(csv.DictReader(f))
    assert row["term"] == "ephemeral"
    assert row["synonyms"] == "transient, fleeting, momentary"
    assert row["example_sentences"] == " | ".join(sample_word.example_sentences)
    assert row["is_favorite"] == "hayır"
    assert len(row["created_at"]) == 10  # yalnızca tarih


def test_csv_round_trip(
    export_service: ExportService, repo: WordRepository, tmp_path, sample_word: Word
):
    repo.create(sample_word)
    target = tmp_path / "out.csv"
    export_service.export_csv(target)
    repo.delete_all()

    imported, skipped = export_service.import_csv(target)

    assert (imported, skipped) == (1, 0)
    restored = repo.get_all()[0]
    assert restored.term == "ephemeral"
    assert restored.synonyms == ["transient", "fleeting", "momentary"]
    assert restored.example_sentences == sample_word.example_sentences
    assert restored.tags == ["vocabulary", "adjective"]
    assert restored.ai_generated is False  # elle içe aktarım AI üretimi sayılmaz


def test_import_csv_skips_rows_without_term(
    export_service: ExportService, repo: WordRepository, tmp_path
):
    target = tmp_path / "in.csv"
    target.write_text(
        "term,language\nvalid,en\n,en\n  ,en\n",
        encoding="utf-8-sig",
    )

    imported, skipped = export_service.import_csv(target)

    assert (imported, skipped) == (1, 2)
    assert repo.get_all()[0].term == "valid"


def test_import_csv_defaults_language_to_en(
    export_service: ExportService, repo: WordRepository, tmp_path
):
    target = tmp_path / "in.csv"
    target.write_text("term\nserendipity\n", encoding="utf-8-sig")

    imported, _ = export_service.import_csv(target)

    assert imported == 1
    assert repo.get_all()[0].language == "en"


def test_import_csv_rejects_missing_file(export_service: ExportService, tmp_path):
    with pytest.raises(LexisImportError):
        export_service.import_csv(tmp_path / "yok.csv")
