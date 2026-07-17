"""
Lexis — Tests: AI Service yardımcıları (API gerektirmez)
"""

import json
import time
from types import SimpleNamespace

import pytest
from google import genai

from lexis.domain.exceptions import AIServiceError, APIKeyMissingError
from lexis.services.ai_service import (
    MAX_ATTEMPTS,
    REQUEST_TIMEOUT_MS,
    AIService,
    ExampleSentence,
    WordData,
    _build_prompt,
    _format_examples,
    _is_retryable,
)


def test_format_examples_from_pydantic():
    raw = [
        ExampleSentence(foreign="I love apples.", turkish="Elma severim."),
        ExampleSentence(foreign="She runs fast.", turkish="O hızlı koşar."),
    ]
    out = _format_examples(raw)
    assert out == ["I love apples.\nElma severim.", "She runs fast.\nO hızlı koşar."]


def test_format_examples_from_dicts():
    raw = [{"foreign": "Good morning.", "turkish": "Günaydın."}]
    assert _format_examples(raw) == ["Good morning.\nGünaydın."]


def test_format_examples_foreign_only():
    raw = [{"foreign": "Hello.", "turkish": ""}]
    assert _format_examples(raw) == ["Hello."]


def test_format_examples_legacy_flat_pairs():
    raw = ["A.", "Ç1.", "B.", "Ç2."]
    assert _format_examples(raw) == ["A.\nÇ1.", "B.\nÇ2."]


def test_format_examples_empty():
    assert _format_examples([]) == []
    assert _format_examples(None) == []


# ── Prompt kurulumu ───────────────────────────────────────────────────────

def test_prompt_includes_term_and_language_name():
    prompt = _build_prompt("ephemeral", "de")
    assert "ephemeral" in prompt
    assert "Almanca" in prompt  # dil kodu değil, okunabilir ad


def test_prompt_falls_back_to_code_for_unknown_language():
    assert "xx" in _build_prompt("word", "xx")


# ── Yapılandırma ──────────────────────────────────────────────────────────

def test_is_not_configured_without_key():
    assert AIService(api_key=None).is_configured is False


def test_generate_without_key_raises():
    with pytest.raises(APIKeyMissingError):
        AIService(api_key=None).generate_word_data("word", "en")


def test_configure_sets_timeout(monkeypatch):
    """Zaman aşımı olmadan asılı bir istek worker thread'ini süresiz bloklar."""
    captured = {}

    class FakeClient:
        def __init__(self, api_key, http_options=None):
            captured["api_key"] = api_key
            captured["timeout"] = http_options.timeout if http_options else None

    monkeypatch.setattr(genai, "Client", FakeClient)
    service = AIService(api_key="k")

    assert service.is_configured is True
    assert captured["api_key"] == "k"
    assert captured["timeout"] == REQUEST_TIMEOUT_MS


# ── Yeniden deneme ────────────────────────────────────────────────────────

class _FakeResponse:
    def __init__(self, parsed=None, finish_reason="STOP", block_reason=None):
        self.parsed = parsed
        self.text = "{}"
        self.prompt_feedback = SimpleNamespace(block_reason=block_reason)
        self.candidates = [SimpleNamespace(finish_reason=finish_reason)]


def _word_data() -> WordData:
    return WordData(
        definition="tanım", definition_short="kısa", part_of_speech="isim",
        synonyms=["a"], antonyms=["b"],
        example_sentences=[ExampleSentence(foreign="F", turkish="T")],
        usage_notes="not",
    )


def _service_with(monkeypatch, side_effects: list) -> AIService:
    """side_effects: her çağrıda sırayla döndürülecek/fırlatılacak değerler."""
    calls = {"n": 0}

    def generate_content(model, contents, config):
        item = side_effects[calls["n"]]
        calls["n"] += 1
        if isinstance(item, Exception):
            raise item
        return item

    class FakeClient:
        def __init__(self, *a, **k):
            self.models = SimpleNamespace(generate_content=generate_content)

    monkeypatch.setattr(genai, "Client", FakeClient)
    service = AIService(api_key="k")
    service._calls = calls
    return service


def test_retries_transient_error_then_succeeds(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda _s: None)  # testi bekletme
    service = _service_with(monkeypatch, [
        RuntimeError("503 Service Unavailable"),
        _FakeResponse(parsed=_word_data()),
    ])

    data = service.generate_word_data("word", "en")

    assert data["definition"] == "tanım"
    assert service._calls["n"] == 2  # bir kez yeniden denendi


def test_gives_up_after_max_attempts(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda _s: None)
    service = _service_with(monkeypatch, [RuntimeError("429 rate limit")] * MAX_ATTEMPTS)

    with pytest.raises(AIServiceError):
        service.generate_word_data("word", "en")

    assert service._calls["n"] == MAX_ATTEMPTS


def test_permanent_error_is_not_retried(monkeypatch):
    """Geçersiz anahtar gibi kalıcı hatada yeniden denemek kullanıcıyı bekletir."""
    monkeypatch.setattr(time, "sleep", lambda _s: None)
    service = _service_with(monkeypatch, [RuntimeError("400 API key not valid")])

    with pytest.raises(AIServiceError):
        service.generate_word_data("word", "en")

    assert service._calls["n"] == 1


@pytest.mark.parametrize("error,retryable", [
    (RuntimeError("429 too many requests"), True),
    (RuntimeError("503 unavailable"), True),
    (RuntimeError("connection reset"), True),
    (RuntimeError("request timed out"), True),
    (RuntimeError("400 invalid argument"), False),
    (RuntimeError("permission denied"), False),
])
def test_retryable_classification(error, retryable):
    assert _is_retryable(error) is retryable


# ── Güvenlik / boş yanıt denetimi ─────────────────────────────────────────

def test_blocked_prompt_gives_clear_message(monkeypatch):
    service = _service_with(monkeypatch, [_FakeResponse(block_reason="SAFETY")])

    with pytest.raises(AIServiceError, match="güvenlik filtresi"):
        service.generate_word_data("word", "en")


def test_safety_finish_reason_gives_clear_message(monkeypatch):
    service = _service_with(monkeypatch, [
        _FakeResponse(parsed=_word_data(), finish_reason="SAFETY")
    ])

    with pytest.raises(AIServiceError, match="güvenlik filtresi"):
        service.generate_word_data("word", "en")


def test_max_tokens_gives_clear_message(monkeypatch):
    service = _service_with(monkeypatch, [
        _FakeResponse(parsed=_word_data(), finish_reason="MAX_TOKENS")
    ])

    with pytest.raises(AIServiceError, match="uzunluk sınırına"):
        service.generate_word_data("word", "en")


def test_empty_candidates_gives_clear_message(monkeypatch):
    response = _FakeResponse(parsed=_word_data())
    response.candidates = []
    service = _service_with(monkeypatch, [response])

    with pytest.raises(AIServiceError, match="boş yanıt"):
        service.generate_word_data("word", "en")


def test_falls_back_to_parsing_text_when_parsed_missing(monkeypatch):
    """SDK doğrulanmış nesne vermezse ham metin ayrıştırılır."""
    response = _FakeResponse(parsed=None)
    response.text = json.dumps({
        "definition": "metinden", "definition_short": "kısa",
        "part_of_speech": "isim", "synonyms": [], "antonyms": [],
        "example_sentences": [], "usage_notes": "",
    })
    service = _service_with(monkeypatch, [response])

    assert service.generate_word_data("word", "en")["definition"] == "metinden"


def test_unparsable_text_raises(monkeypatch):
    response = _FakeResponse(parsed=None)
    response.text = "JSON değil"
    service = _service_with(monkeypatch, [response])

    with pytest.raises(AIServiceError, match="ayrıştırılamadı"):
        service.generate_word_data("word", "en")
