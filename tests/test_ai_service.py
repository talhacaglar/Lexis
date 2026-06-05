"""
Lexis — Tests: AI Service yardımcıları (API gerektirmez)
"""

from lexis.services.ai_service import ExampleSentence, _format_examples


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
