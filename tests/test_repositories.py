"""
Lexis — Tests: Word Repository
"""

import pytest
from lexis.domain.models import Word, WordStatus
from lexis.domain.exceptions import WordNotFoundError, DatabaseError
from lexis.persistence.word_repository import WordRepository


class TestWordRepositoryCreate:
    def test_create_returns_word(self, repo: WordRepository, sample_word: Word):
        result = repo.create(sample_word)
        assert result.id == sample_word.id
        assert result.term == "ephemeral"

    def test_created_word_is_retrievable(self, repo: WordRepository, sample_word: Word):
        repo.create(sample_word)
        fetched = repo.get_by_id(sample_word.id)
        assert fetched.term == sample_word.term
        assert fetched.synonyms == sample_word.synonyms

    def test_json_fields_round_trip(self, repo: WordRepository, sample_word: Word):
        repo.create(sample_word)
        fetched = repo.get_by_id(sample_word.id)
        assert fetched.synonyms == ["transient", "fleeting", "momentary"]
        assert fetched.antonyms == ["permanent", "eternal", "lasting"]
        assert len(fetched.example_sentences) == 2
        assert fetched.tags == ["vocabulary", "adjective"]


class TestWordRepositoryRead:
    def test_get_by_id_raises_not_found(self, repo: WordRepository):
        with pytest.raises(WordNotFoundError):
            repo.get_by_id("nonexistent-id")

    def test_get_all_returns_all_words(self, repo: WordRepository, sample_word: Word):
        w2 = Word(term="serendipity", language="en")
        repo.create(sample_word)
        repo.create(w2)
        results = repo.get_all()
        assert len(results) == 2

    def test_search_filters_by_term(self, repo: WordRepository, sample_word: Word):
        w2 = Word(term="serendipity", language="en")
        repo.create(sample_word)
        repo.create(w2)
        results = repo.get_all(search="ephemeral")
        assert len(results) == 1
        assert results[0].term == "ephemeral"

    def test_filter_by_status(self, repo: WordRepository, sample_word: Word):
        w2 = Word(term="serendipity", language="en", status=WordStatus.LEARNED)
        repo.create(sample_word)
        repo.create(w2)
        results = repo.get_all(status=WordStatus.LEARNED)
        assert len(results) == 1
        assert results[0].status == WordStatus.LEARNED

    def test_filter_favorites(self, repo: WordRepository, sample_word: Word):
        sample_word.is_favorite = True
        w2 = Word(term="serendipity", language="en")
        repo.create(sample_word)
        repo.create(w2)
        results = repo.get_all(favorites_only=True)
        assert len(results) == 1
        assert results[0].is_favorite is True

    def test_exists_returns_true_for_existing(self, repo: WordRepository, sample_word: Word):
        repo.create(sample_word)
        assert repo.exists("ephemeral", "en") is True

    def test_exists_returns_false_for_missing(self, repo: WordRepository):
        assert repo.exists("unknown", "en") is False

    def test_get_stats(self, repo: WordRepository, sample_word: Word):
        w2 = Word(term="serendipity", language="en", status=WordStatus.LEARNED)
        repo.create(sample_word)
        repo.create(w2)
        stats = repo.get_stats()
        assert stats.total == 2
        assert stats.learned == 1
        assert stats.new == 1


class TestWordRepositoryUpdate:
    def test_update_changes_status(self, repo: WordRepository, sample_word: Word):
        repo.create(sample_word)
        sample_word.status = WordStatus.LEARNED
        repo.update(sample_word)
        fetched = repo.get_by_id(sample_word.id)
        assert fetched.status == WordStatus.LEARNED

    def test_update_changes_tags(self, repo: WordRepository, sample_word: Word):
        repo.create(sample_word)
        sample_word.tags = ["new_tag"]
        repo.update(sample_word)
        fetched = repo.get_by_id(sample_word.id)
        assert fetched.tags == ["new_tag"]


class TestWordRepositoryDelete:
    def test_delete_removes_word(self, repo: WordRepository, sample_word: Word):
        repo.create(sample_word)
        repo.delete(sample_word.id)
        with pytest.raises(WordNotFoundError):
            repo.get_by_id(sample_word.id)

    def test_delete_all(self, repo: WordRepository, sample_word: Word):
        repo.create(sample_word)
        count = repo.delete_all()
        assert count == 1
        assert repo.get_all() == []
