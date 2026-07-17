"""
Lexis — Widget: Add Word Dialog

Yeni kelime ekleme ve AI içerik üretimi diyalogu.
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from lexis.domain.models import SUPPORTED_LANGUAGES
from lexis.services.word_service import WordService
from lexis.ui.animations import DURATION_FAST, fade_in
from lexis.ui.theme import repolish
from lexis.ui.widgets.common import ClickableChip, Divider, SectionLabel
from lexis.ui.widgets.loading_overlay import LoadingOverlay
from lexis.workers.task_worker import TaskWorker

logger = logging.getLogger(__name__)

# Yazma duraklamasından sonra öneri istemeye kadar beklenen süre. 350 ms:
# ortalama yazma hızında tuşlar arası boşluğun üstünde (her harfte istek
# atılmaz) ama kullanıcı beklediğini hissetmeyecek kadar kısa.
TYPING_DEBOUNCE_MS = 350


class AddWordDialog(QDialog):
    """
    Kelime ekleme diyalogu.
    Kullanıcı bir kelime girer, dili seçer,
    AI ile içerik üretir ve kaydeder.
    """

    word_added = pyqtSignal(str)  # word_id

    def __init__(self, word_service: WordService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = word_service
        self._ai_worker: TaskWorker | None = None
        self._suggest_worker: TaskWorker | None = None
        self._ai_data: dict | None = None
        self._suggestion_chips: list[ClickableChip] = []
        # Geciken bir yanıt, kullanıcı yazmaya devam ettiyse artık eskimiştir.
        # Her istek numaralanır; yalnızca en sonuncunun yanıtı ekrana yazılır.
        self._suggest_request_id = 0

        self._typing_timer = QTimer(self)
        self._typing_timer.setSingleShot(True)

        self._setup_ui()
        self._setup_connections()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Yeni Kelime Ekle")
        self.setModal(True)
        # Buton ve yüzey stilleri global QSS'ten gelir; buradaki yerel kopyalar
        # uygulamanın geri kalanından farklı renkler üretiyordu.
        self.setMinimumSize(560, 620)
        self.resize(560, 680)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──
        header = QWidget()
        header.setObjectName("dialogHeader")
        header.setFixedHeight(70)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(24, 0, 24, 0)

        title = QLabel("Yeni Kelime Ekle")
        title.setObjectName("dialogTitle")

        close_btn = QPushButton("×")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(32, 32)
        close_btn.setToolTip("Kapat")
        close_btn.setAccessibleName("Kapat")
        close_btn.clicked.connect(self.reject)

        h_layout.addWidget(title, 1)
        h_layout.addWidget(close_btn)
        root.addWidget(header)

        # ── Scrollable Content ──
        # Saydam zemin global QSS'teki QScrollArea kuralından gelir. Burada
        # widget'a stylesheet vermek tüm alt ağaca sızıyor ve içerideki
        # butonları/açılır menüleri de saydam yapıyordu (siyah üstüne siyah).
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content.setObjectName("dialogSurface")
        form = QVBoxLayout(content)
        form.setContentsMargins(24, 24, 24, 24)
        form.setSpacing(20)

        # ── Word Input + Language ──
        row1 = QHBoxLayout()
        row1.setSpacing(12)

        word_col = QVBoxLayout()
        word_col.setSpacing(6)
        word_col.addWidget(SectionLabel("KELİME"))
        self._term_input = QLineEdit()
        self._term_input.setPlaceholderText("örn. ephemeral")
        self._term_input.setMinimumHeight(44)
        word_col.addWidget(self._term_input)
        row1.addLayout(word_col, 2)

        lang_col = QVBoxLayout()
        lang_col.setSpacing(6)
        lang_col.addWidget(SectionLabel("DİL"))
        self._lang_combo = QComboBox()
        self._lang_combo.setMinimumHeight(44)
        for code, name in SUPPORTED_LANGUAGES.items():
            self._lang_combo.addItem(name, code)
        lang_col.addWidget(self._lang_combo)
        row1.addLayout(lang_col, 1)

        form.addLayout(row1)

        # ── Generate Button ──
        self._generate_btn = QPushButton("  ✨  İçerik Üret")
        self._generate_btn.setObjectName("primaryBtn")
        self._generate_btn.setMinimumHeight(44)
        self._generate_btn.setEnabled(False)
        form.addWidget(self._generate_btn)

        # Durum metni (üretim sonucu/hatası) — footer'daki dar alan yerine
        # burada tam genişlikte ve satır kaydırmalı: uzun "bulunamadı" mesajı
        # kırpılmadan, kelimenin hemen altında görünür.
        self._status_label = QLabel("")
        self._status_label.setObjectName("statusText")
        self._status_label.setWordWrap(True)
        form.addWidget(self._status_label)

        # ── Öneriler ──
        # Yazarken tamamlama, bulunamayınca düzeltme. İkisi de kendiliğinden
        # belirir; ayrıca bir şeye tıklamak gerekmez.
        self._suggestions_widget = QWidget()
        self._suggestions_widget.setVisible(False)
        sugg_layout = QVBoxLayout(self._suggestions_widget)
        sugg_layout.setContentsMargins(0, 0, 0, 0)
        sugg_layout.setSpacing(8)
        # Başlık bağlama göre değişir: yazarken tamamlama, hatadan sonra düzeltme.
        self._suggestions_title = SectionLabel("ÖNERİLER")
        sugg_layout.addWidget(self._suggestions_title)

        self._suggestions_row = QHBoxLayout()
        self._suggestions_row.setSpacing(8)
        self._suggestions_row.addStretch()
        sugg_layout.addLayout(self._suggestions_row)
        form.addWidget(self._suggestions_widget)

        # ── AI Result Fields ──
        self._result_widget = QWidget()
        self._result_widget.setVisible(False)
        result_layout = QVBoxLayout(self._result_widget)
        result_layout.setContentsMargins(0, 0, 0, 0)
        result_layout.setSpacing(16)

        # Separator
        result_layout.addWidget(Divider())

        # Short definition
        result_layout.addWidget(SectionLabel("KISA TANIM"))
        self._short_def = QLineEdit()
        self._short_def.setReadOnly(False)
        self._short_def.setMinimumHeight(40)
        result_layout.addWidget(self._short_def)

        # Full definition
        result_layout.addWidget(SectionLabel("TANIM"))
        self._definition = QTextEdit()
        self._definition.setMinimumHeight(90)
        self._definition.setMaximumHeight(120)
        result_layout.addWidget(self._definition)

        # Part of speech
        result_layout.addWidget(SectionLabel("SÖZCÜK TÜRÜ"))
        self._pos_input = QLineEdit()
        self._pos_input.setMinimumHeight(40)
        result_layout.addWidget(self._pos_input)

        # Synonyms
        result_layout.addWidget(SectionLabel("EŞ ANLAMLILAR (virgülle ayırın)"))
        self._synonyms_input = QLineEdit()
        self._synonyms_input.setMinimumHeight(40)
        result_layout.addWidget(self._synonyms_input)

        # Antonyms
        result_layout.addWidget(SectionLabel("ZIT ANLAMLILAR (virgülle ayırın)"))
        self._antonyms_input = QLineEdit()
        self._antonyms_input.setMinimumHeight(40)
        result_layout.addWidget(self._antonyms_input)

        # Example sentences
        result_layout.addWidget(SectionLabel("ÖRNEK CÜMLELER"))
        self._examples_input = QTextEdit()
        self._examples_input.setMinimumHeight(80)
        self._examples_input.setMaximumHeight(100)
        self._examples_input.setPlaceholderText("Her satıra bir cümle...")
        result_layout.addWidget(self._examples_input)

        # Usage notes
        result_layout.addWidget(SectionLabel("KULLANIM NOTU"))
        self._usage_notes = QTextEdit()
        self._usage_notes.setMinimumHeight(70)
        self._usage_notes.setMaximumHeight(90)
        result_layout.addWidget(self._usage_notes)

        form.addWidget(self._result_widget)
        form.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        # ── Footer ──
        footer = QWidget()
        footer.setObjectName("dialogFooter")
        footer.setFixedHeight(70)
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(24, 0, 24, 0)
        f_layout.setSpacing(12)
        f_layout.addStretch()

        cancel_btn = QPushButton("İptal")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.setMinimumWidth(90)
        cancel_btn.clicked.connect(self.reject)
        f_layout.addWidget(cancel_btn)

        self._save_btn = QPushButton("Kaydet")
        self._save_btn.setObjectName("primaryBtn")
        self._save_btn.setMinimumHeight(40)
        self._save_btn.setMinimumWidth(100)
        self._save_btn.setEnabled(False)
        f_layout.addWidget(self._save_btn)

        root.addWidget(footer)

        # ── Loading Overlay ──
        self._loading = LoadingOverlay(self, "AI içerik üretiliyor...")

    def _setup_connections(self) -> None:
        self._term_input.textChanged.connect(self._on_term_changed)
        self._generate_btn.clicked.connect(self._generate_ai_content)
        self._save_btn.clicked.connect(self._save_word)
        self._typing_timer.timeout.connect(self._fetch_completions)

    def _on_term_changed(self, text: str) -> None:
        has_text = bool(text.strip())
        self._generate_btn.setEnabled(has_text)

        # Her tuş vuruşunda ağa çıkmak hem yavaş hem gereksiz: yazma durunca
        # tek istek atılır.
        self._typing_timer.start(TYPING_DEBOUNCE_MS)
        if not has_text:
            self._clear_suggestions()

    def _generate_ai_content(self) -> None:
        term = self._term_input.text().strip()
        if not term:
            return

        # Süren bir üretim varken ikinci worker başlatmak, iki yanıtın
        # birbirinin üstüne yazmasına yol açardı.
        if self._ai_worker is not None and self._ai_worker.isRunning():
            return

        lang_code = self._lang_combo.currentData()
        self._loading.show_loading(
            f"'{term}' için içerik üretiliyor ({self._service.content_source})..."
        )
        self._generate_btn.setEnabled(False)
        self._clear_suggestions()  # önceki denemenin önerileri kalmasın

        self._ai_worker = TaskWorker(
            lambda: self._service.generate_content(term, lang_code), parent=self
        )
        self._ai_worker.succeeded.connect(self._on_ai_finished)
        self._ai_worker.failed.connect(self._on_ai_error)
        self._ai_worker.finished.connect(self._clear_worker)
        self._ai_worker.start()

    def _clear_worker(self) -> None:
        """Biten worker'ı bırakır; aksi hâlde Qt sahipliği nedeniyle birikirler."""
        if self._ai_worker is not None:
            self._ai_worker.deleteLater()
            self._ai_worker = None

    def _on_ai_finished(self, data: dict) -> None:
        self._loading.hide_loading()
        self._ai_data = data
        self._populate_fields(data)
        was_hidden = not self._result_widget.isVisible()
        self._result_widget.setVisible(True)
        self._save_btn.setEnabled(True)
        self._generate_btn.setEnabled(True)
        self._set_status("✓ İçerik üretildi", "success")
        if was_hidden:
            fade_in(self._result_widget)

    def _set_status(self, message: str, level: str = "info") -> None:
        """
        Durum metnini günceller. Renk QSS'teki #statusText[level="..."]
        kuralından gelir, böylece tema değişiminde yeniden boyanır.
        """
        self._status_label.setText(message)
        self._status_label.setProperty("level", level)
        repolish(self._status_label)

    def _on_ai_error(self, message: str) -> None:
        self._loading.hide_loading()
        self._generate_btn.setEnabled(True)
        self._set_status(f"Hata: {message}", "error")
        # Hata olsa bile kaydetmeye izin ver (boş veriyle)
        self._result_widget.setVisible(True)
        self._save_btn.setEnabled(True)
        self._fetch_suggestions()

    # ── Öneriler: yazarken tamamlama, hatadan sonra düzeltme ──────────────

    def _fetch_completions(self) -> None:
        """Yazma durunca kelimeyi tamamlar (debounce zamanlayıcısı tetikler)."""
        prefix = self._term_input.text().strip()
        self._start_suggest_worker(
            lambda lang: self._service.complete_terms(prefix, lang),
            title="ÖNERİLER",
        )

    def _fetch_suggestions(self) -> None:
        """
        Başarısız üretimden sonra alternatifleri arar.

        Her hatada denenir: yazım hatası en olası sebep. Ağ ya da anahtar
        kaynaklı hatalarda arama da sonuç veremez, satır gizli kalır.
        """
        term = self._term_input.text().strip()
        if not term:
            return
        self._typing_timer.stop()  # tamamlama düzeltmenin üstüne yazmasın
        self._start_suggest_worker(
            lambda lang: self._service.suggest_terms(term, lang),
            title="ŞUNU MU DEMEK İSTEDİNİZ?",
        )

    def _start_suggest_worker(self, fetch, title: str) -> None:
        """
        Öneri aramasını arka planda başlatır.

        İstekler numaralanır: yavaş bir yanıt, kullanıcı yazmaya devam edip yeni
        bir istek tetiklediyse ekrana yazılmaz. Numara olmasa geciken "rec"
        yanıtı, ekrandaki "recieve" önerilerinin üstüne binerdi.
        """
        self._suggest_request_id += 1
        request_id = self._suggest_request_id
        lang_code = self._lang_combo.currentData()

        worker = TaskWorker(lambda: fetch(lang_code), parent=self)
        worker.succeeded.connect(lambda words: self._show_suggestions(words, request_id, title))
        # Öneri bir kolaylık: bulunamazsa kullanıcıyı ikinci bir hatayla yorma.
        worker.failed.connect(lambda msg: logger.info("Öneri alınamadı: %s", msg))
        worker.finished.connect(worker.deleteLater)
        self._suggest_worker = worker
        worker.start()

    def _show_suggestions(self, words: list[str], request_id: int, title: str) -> None:
        if request_id != self._suggest_request_id:
            return  # eskimiş yanıt

        self._clear_suggestions()
        if not words:
            return

        self._suggestions_title.setText(title)
        for word in words:
            chip = ClickableChip(word)
            chip.setToolTip(f"'{word}' için içerik üret")
            chip.clicked.connect(self._use_suggestion)
            self._suggestion_chips.append(chip)
            # addStretch en sonda; chip'ler onun önüne girmeli.
            self._suggestions_row.insertWidget(self._suggestions_row.count() - 1, chip)

        self._suggestions_widget.setVisible(True)
        # Chip'ler küçük: yazarken sık belirdikleri için hızlı olmalılar.
        fade_in(self._suggestions_widget, DURATION_FAST)

    def _clear_suggestions(self) -> None:
        for chip in self._suggestion_chips:
            self._suggestions_row.removeWidget(chip)
            chip.deleteLater()
        self._suggestion_chips.clear()
        self._suggestions_widget.setVisible(False)

    def _use_suggestion(self, word: str) -> None:
        """Öneriye tıklayınca kelimeyi değiştirip yeniden üretir."""
        self._term_input.setText(word)
        self._clear_suggestions()
        self._generate_ai_content()

    def _populate_fields(self, data: dict) -> None:
        self._short_def.setText(data.get("definition_short", ""))
        self._definition.setPlainText(data.get("definition", ""))
        self._pos_input.setText(data.get("part_of_speech", ""))
        self._synonyms_input.setText(", ".join(data.get("synonyms", [])))
        self._antonyms_input.setText(", ".join(data.get("antonyms", [])))
        self._examples_input.setPlainText("\n\n".join(data.get("example_sentences", [])))
        self._usage_notes.setPlainText(data.get("usage_notes", ""))

    def _collect_ai_data(self) -> dict:
        """Formdan güncel AI verisini toplar."""
        synonyms = [s.strip() for s in self._synonyms_input.text().split(",") if s.strip()]
        antonyms = [a.strip() for a in self._antonyms_input.text().split(",") if a.strip()]
        examples_text = self._examples_input.toPlainText().strip()
        import re

        examples = [e.strip() for e in re.split(r"\n\s*\n", examples_text) if e.strip()]

        return {
            "definition": self._definition.toPlainText().strip(),
            "definition_short": self._short_def.text().strip(),
            "part_of_speech": self._pos_input.text().strip(),
            "synonyms": synonyms,
            "antonyms": antonyms,
            "example_sentences": examples,
            "usage_notes": self._usage_notes.toPlainText().strip(),
        }

    def _save_word(self) -> None:
        term = self._term_input.text().strip()
        lang_code = self._lang_combo.currentData()
        ai_data = self._collect_ai_data() if self._result_widget.isVisible() else None

        try:
            word = self._service.add_word(term, lang_code, ai_data=ai_data)
            self.word_added.emit(word.id)
            self.accept()
        except Exception as e:
            logger.exception("Kelime kaydedilemedi")
            self._set_status(str(e), "error")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._loading.resize(self.size())
