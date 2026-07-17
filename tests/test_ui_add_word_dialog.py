"""
Lexis — Tests: Kelime ekleme diyaloğu (görünürlük ve anahtar yönetimi)
"""

import pytest

pytest.importorskip("PyQt6.QtWidgets")

from PyQt6.QtWidgets import QScrollArea, QStyleFactory  # noqa: E402

from lexis.domain.exceptions import ContentProviderError  # noqa: E402
from lexis.services.word_service import WordService  # noqa: E402
from lexis.ui.theme import Colors  # noqa: E402
from lexis.ui.widgets.add_word_dialog import AddWordDialog  # noqa: E402


@pytest.fixture
def dialog(qtbot, word_service: WordService, monkeypatch) -> AddWordDialog:
    # Dil algılama ağa çıkar; testte sahte tutulmazsa arka plan worker'ı
    # diyalog kapandıktan sonra çalışmaya devam edip süreci çökertiyor.
    monkeypatch.setattr(word_service, "detect_language", lambda term: "en")
    monkeypatch.setattr(word_service, "detect_languages", lambda term: ["en"])
    d = AddWordDialog(word_service)
    qtbot.addWidget(d)
    d.resize(560, 680)
    d.show()
    qtbot.waitExposed(d)
    return d


def _background_pixel(widget) -> str:
    """
    Widget'ın zemin rengini örnekler.

    Merkez değil: orada metin var ve kenar yumuşatma yüzünden karışık bir ton
    okunuyor. Metin ortalandığı için sol iç kenar güvenli.
    """
    img = widget.grab().toImage()
    return img.pixelColor(20, img.height() // 2).name().lower()


# ── Stil sızıntısı regresyonu ─────────────────────────────────────────────


def test_scroll_area_has_no_widget_stylesheet(dialog):
    """
    QScrollArea'ya widget seviyesinde stylesheet verilmemeli.

    Seçicisiz bir kural ("background: transparent") tüm alt ağaca sızıyor ve
    içerideki butonları/açılır menüleri saydam yapıyordu. Saydam zemin zaten
    global QSS'teki QScrollArea kuralından geliyor.
    """
    scroll = dialog.findChild(QScrollArea)
    assert scroll is not None
    assert scroll.styleSheet() == ""


def test_generate_button_is_not_black_on_black(dialog, qtbot):
    """
    'İçerik Üret' butonu scroll alanının içinde; sızan saydamlık yüzünden
    zemini siyaha dönüp metniyle birlikte okunamaz hâle geliyordu.
    """
    dialog._term_input.setText("thug")  # butonu etkinleştir
    qtbot.wait(50)

    assert dialog._generate_btn.isEnabled()
    assert _background_pixel(dialog._generate_btn) == Colors.BTN_BG.lower()


def test_language_popup_uses_theme_background(dialog, qtbot):
    """
    Dil açılır menüsü de scroll alanının çocuğu: sızıntı yüzünden zemini
    beyaz kalıp açık renk metinle okunamıyordu.
    """
    if "fusion" not in {s.lower() for s in QStyleFactory.keys()}:
        pytest.skip("Fusion stili yok")

    dialog._lang_combo.showPopup()
    qtbot.wait(50)
    popup = dialog._lang_combo.view().window()

    assert _background_pixel(popup) == Colors.BG_ELEVATED.lower()
    dialog._lang_combo.hidePopup()


# ── Hata görünürlüğü ──────────────────────────────────────────────────────


# ── Dil algılama ──────────────────────────────────────────────────────────


def test_language_is_detected_not_asked(dialog, qtbot, monkeypatch):
    """Kullanıcıdan dil istenmez: kelimeden algılanıp seçiciye yansıtılır."""
    monkeypatch.setattr(dialog._service, "detect_languages", lambda term: ["de"])
    monkeypatch.setattr(dialog._service, "generate_content", lambda t, lang: {"definition": lang})

    dialog._term_input.setText("Haus")
    dialog._generate_ai_content()
    qtbot.waitUntil(lambda: dialog._result_widget.isVisible(), timeout=2000)

    assert dialog._lang_combo.currentData() == "de"


def test_detected_language_does_not_trigger_regeneration(dialog, qtbot, monkeypatch):
    """
    Algılanan dili seçiciye yazmak, "kullanıcı düzeltti" sayılmamalı.

    Sayılsaydı sonsuz yeniden üretim döngüsü olurdu.
    """
    monkeypatch.setattr(dialog._service, "detect_languages", lambda term: ["de"])
    calls: list[str] = []
    monkeypatch.setattr(
        dialog._service,
        "generate_content",
        lambda t, lang: calls.append(lang) or {"definition": "x"},
    )

    dialog._term_input.setText("Haus")
    dialog._generate_ai_content()
    qtbot.waitUntil(lambda: dialog._result_widget.isVisible(), timeout=2000)
    qtbot.wait(200)

    assert calls == ["de"]


def test_correcting_language_regenerates_content(dialog, qtbot, monkeypatch):
    """Algılama yanılabilir; düzeltince içerik o dile göre yeniden üretilir."""
    calls: list[str] = []
    monkeypatch.setattr(
        dialog._service,
        "generate_content",
        lambda t, lang: calls.append(lang) or {"definition": "x"},
    )

    dialog._term_input.setText("Haus")
    dialog._generate_ai_content()
    qtbot.waitUntil(lambda: dialog._result_widget.isVisible(), timeout=2000)

    dialog._lang_combo.setCurrentIndex(dialog._lang_combo.findData("de"))
    qtbot.waitUntil(lambda: calls == ["en", "de"], timeout=2000)

    assert dialog._lang_combo.currentData() == "de"


def test_error_shows_the_attempted_language_not_a_stale_one(dialog, qtbot, monkeypatch):
    """
    Regresyon (ekran görüntüsündeki hata): "Tahanan" için "İngilizce'de yok"
    hatası gösterilirken seçici, önceki kelimeden kalan dili ("Arapça")
    gösteriyordu; öneriler de o yanlış dilde aranıyordu.
    """
    monkeypatch.setattr(dialog._service, "complete_terms", lambda p, lang: [])
    monkeypatch.setattr(dialog._service, "suggest_terms", lambda term, lang: [])

    # 1) Önce bir kelime "de" olarak başarıyla üretilir.
    monkeypatch.setattr(dialog._service, "detect_languages", lambda term: ["de"])
    monkeypatch.setattr(dialog._service, "generate_content", lambda t, lang: {"definition": "x"})

    dialog._term_input.setText("Haus")
    dialog._generate_ai_content()
    qtbot.waitUntil(lambda: dialog._lang_combo.currentData() == "de", timeout=2000)

    # 2) Sonra yalnızca İngilizce aday gösterilen başka bir kelime hata verir.
    monkeypatch.setattr(dialog._service, "detect_languages", lambda term: ["en"])

    def not_found(t, lang):
        raise ContentProviderError(f"'{t}' bulunamadı.")

    monkeypatch.setattr(dialog._service, "generate_content", not_found)

    dialog._term_input.setText("Tahanan")
    dialog._generate_ai_content()
    qtbot.waitUntil(lambda: "bulunamadı" in dialog._status_label.text(), timeout=2000)

    # Seçici bu turda denenen dili göstermeli, bayat "de"yi değil.
    assert dialog._lang_combo.currentData() == "en"


# ── Üretilen içeriğin kilidi ──────────────────────────────────────────────


def test_generated_fields_are_read_only_by_default(dialog):
    """Üretilen içerik kazara değiştirilmemeli."""
    assert all(f.isReadOnly() for f in dialog._content_fields())


def test_edit_button_unlocks_fields(dialog):
    dialog._edit_btn.setChecked(True)
    assert all(not f.isReadOnly() for f in dialog._content_fields())

    dialog._edit_btn.setChecked(False)
    assert all(f.isReadOnly() for f in dialog._content_fields())


def test_short_definition_shows_its_beginning(dialog, qtbot, monkeypatch):
    """
    Uzun tanımda QLineEdit sona kayıp baş harfi kırpıyordu
    ("Genellikle..." yerine "enellikle...").
    """
    long_text = "Genellikle dar gelirli ailelerin barındığı, kalabalık ve bakımsız apartman binası."
    monkeypatch.setattr(
        dialog._service, "generate_content", lambda t, lang: {"definition_short": long_text}
    )

    dialog._term_input.setText("tenement")
    dialog._generate_ai_content()
    qtbot.waitUntil(lambda: dialog._result_widget.isVisible(), timeout=2000)

    assert dialog._short_def.cursorPosition() == 0


# ── Yazarken tamamlama ────────────────────────────────────────────────────


def test_typing_suggests_completions_automatically(dialog, qtbot, monkeypatch):
    """Yazma durunca öneriler kendiliğinden gelmeli; butona basmak gerekmez."""
    monkeypatch.setattr(dialog._service, "complete_terms", lambda p, lang: ["ephemeral"])

    dialog._term_input.setText("ephem")
    qtbot.waitUntil(lambda: bool(dialog._suggestion_chips), timeout=2000)

    assert [c.text() for c in dialog._suggestion_chips] == ["ephemeral"]
    assert "ÖNERİ" in dialog._suggestions_title.text()


def test_typing_does_not_hit_network_on_every_keystroke(dialog, qtbot, monkeypatch):
    """Her tuşta istek atmak hem yavaş hem gereksiz: yazma durunca tek istek."""
    calls: list[str] = []
    monkeypatch.setattr(dialog._service, "complete_terms", lambda p, lang: calls.append(p) or [])

    for text in ["e", "ep", "eph", "ephe", "ephem"]:
        dialog._term_input.setText(text)
        qtbot.wait(30)  # debounce süresinden kısa

    qtbot.wait(600)
    assert calls == ["ephem"]


def test_stale_completion_does_not_overwrite_newer_one(dialog, qtbot, monkeypatch):
    """
    Geciken bir yanıt, kullanıcı yazmaya devam ettiyse ekrana yazılmamalı.
    """
    monkeypatch.setattr(dialog._service, "complete_terms", lambda p, lang: [f"{p}-sonuc"])

    dialog._term_input.setText("eski")
    qtbot.waitUntil(lambda: bool(dialog._suggestion_chips), timeout=2000)

    # Eskimiş bir isteğin yanıtı sonradan gelirse yok sayılmalı.
    dialog._show_suggestions(["ESKI"], request_id=-1, title="ÖNERİLER")

    assert [c.text() for c in dialog._suggestion_chips] == ["eski-sonuc"]


def test_repeated_prefix_is_served_from_cache(dialog, qtbot, monkeypatch):
    """Harf silip yeniden yazmak yaygın; aynı öneki tekrar ağa sormak bekletir."""
    calls: list[str] = []
    monkeypatch.setattr(
        dialog._service,
        "complete_terms",
        lambda p, lang: calls.append(p) or ["Ephemeral"],
    )

    dialog._term_input.setText("ephem")
    qtbot.waitUntil(lambda: bool(dialog._suggestion_chips), timeout=2000)

    dialog._term_input.setText("ephe")  # geri sil
    qtbot.wait(300)
    dialog._term_input.setText("ephem")  # aynı öneke dön
    qtbot.wait(300)

    assert calls.count("ephem") == 1
    assert [c.text() for c in dialog._suggestion_chips] == ["Ephemeral"]


def test_clearing_input_hides_suggestions(dialog, qtbot, monkeypatch):
    monkeypatch.setattr(dialog._service, "complete_terms", lambda p, lang: ["ephemeral"])
    dialog._term_input.setText("ephem")
    qtbot.waitUntil(lambda: bool(dialog._suggestion_chips), timeout=2000)

    dialog._term_input.setText("")

    assert not dialog._suggestions_widget.isVisible()


# ── "Şunu mu demek istediniz?" ────────────────────────────────────────────


def test_suggestions_appear_automatically_on_failure(dialog, qtbot, monkeypatch):
    """
    Öneriler kendiliğinden listelenmeli; kullanıcı ayrıca bir şeye tıklamamalı.
    """
    monkeypatch.setattr(dialog._service, "suggest_terms", lambda term, lang: ["receive", "relieve"])

    dialog._term_input.setText("recieve")
    dialog._on_ai_error("bulunamadı")
    qtbot.waitUntil(lambda: dialog._suggestions_widget.isVisible(), timeout=2000)

    assert [c.text() for c in dialog._suggestion_chips] == ["receive", "relieve"]


def test_no_suggestions_keeps_row_hidden(dialog, qtbot, monkeypatch):
    """Öneri yoksa boş bir başlık asılı kalmamalı."""
    monkeypatch.setattr(dialog._service, "suggest_terms", lambda term, lang: [])

    dialog._term_input.setText("zzzqqxyz")
    dialog._on_ai_error("bulunamadı")
    qtbot.wait(150)

    assert not dialog._suggestions_widget.isVisible()


def test_suggestion_failure_is_swallowed(dialog, qtbot, monkeypatch):
    """Öneri araması çökerse kullanıcı ikinci bir hatayla karşılaşmamalı."""

    def boom(term, lang):
        raise RuntimeError("ağ yok")

    monkeypatch.setattr(dialog._service, "suggest_terms", boom)

    dialog._term_input.setText("recieve")
    dialog._on_ai_error("bulunamadı")
    qtbot.wait(150)

    assert not dialog._suggestions_widget.isVisible()
    assert "bulunamadı" in dialog._status_label.text()  # asıl hata korunur


def test_clicking_suggestion_regenerates_with_that_word(dialog, qtbot, monkeypatch):
    monkeypatch.setattr(dialog._service, "suggest_terms", lambda term, lang: ["receive"])
    generated: list[str] = []
    monkeypatch.setattr(
        dialog._service,
        "generate_content",
        lambda term, lang: generated.append(term) or {"definition": "x"},
    )

    dialog._term_input.setText("recieve")
    dialog._on_ai_error("bulunamadı")
    qtbot.waitUntil(lambda: bool(dialog._suggestion_chips), timeout=2000)

    dialog._suggestion_chips[0].clicked.emit("receive")
    qtbot.waitUntil(lambda: generated == ["receive"], timeout=2000)

    assert dialog._term_input.text() == "receive"
    assert not dialog._suggestions_widget.isVisible()


def test_new_generation_clears_stale_suggestions(dialog, qtbot, monkeypatch):
    """Önceki denemenin önerileri yeni denemede ekranda kalmamalı."""
    monkeypatch.setattr(dialog._service, "suggest_terms", lambda term, lang: ["receive"])
    monkeypatch.setattr(dialog._service, "generate_content", lambda term, lang: {"definition": "x"})

    dialog._term_input.setText("recieve")
    dialog._on_ai_error("bulunamadı")
    qtbot.waitUntil(lambda: bool(dialog._suggestion_chips), timeout=2000)

    dialog._generate_ai_content()

    assert dialog._suggestion_chips == []
    assert not dialog._suggestions_widget.isVisible()


def test_error_message_is_wrapped_and_outside_footer(dialog):
    """
    'Bulunamadı' mesajı footer'da iki butonun arasına sıkışıp kırpılıyordu;
    kullanıcıya hiçbir şey olmamış gibi görünüyordu.
    """
    dialog._on_ai_error("'Thugger' için açık sözlüklerde kayıt bulunamadı. " * 3)

    assert dialog._status_label.wordWrap()
    assert dialog._status_label.isVisible()
    # Footer sabit 70px; mesaj oraya değil form akışına yerleşmeli.
    assert dialog._status_label.height() > 20
