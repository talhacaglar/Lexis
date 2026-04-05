"""
Lexis — Test Fixtures (conftest.py)
"""

import pytest
from pathlib import Path

from lexis.domain.models import Word, WordStatus
from lexis.persistence.database import Database
from lexis.persistence.word_repository import WordRepository
from lexis.services.ai_service import AIService
from lexis.services.word_service import WordService


@pytest.fixture
def tmp_db(tmp_path: Path) -> Database:
    """Geçici in-memory SQLite veritabanı."""
    return Database(tmp_path / "test.db")


@pytest.fixture
def repo(tmp_db: Database) -> WordRepository:
    return WordRepository(tmp_db)


@pytest.fixture
def ai_service() -> AIService:
    """API anahtarsız (mock) AI servisi."""
    return AIService(api_key=None)


@pytest.fixture
def word_service(repo: WordRepository, ai_service: AIService) -> WordService:
    return WordService(repository=repo, ai_service=ai_service)


@pytest.fixture
def sample_word() -> Word:
    return Word(
        term="ephemeral",
        language="en",
        definition="Lasting for a very short time; transitory.",
        definition_short="Kısa süreli, geçici.",
        synonyms=["transient", "fleeting", "momentary"],
        antonyms=["permanent", "eternal", "lasting"],
        example_sentences=[
            "The ephemeral beauty of cherry blossoms attracts millions of visitors.",
            "Fame can be ephemeral in the age of social media.",
        ],
        usage_notes="Genellikle güzel ama kısa süren şeyler için kullanılır.",
        part_of_speech="Sıfat",
        status=WordStatus.NEW,
        tags=["vocabulary", "adjective"],
    )
