"""
Lexis — Widget: Kelime Düzenleme Diyaloğu

Kelimenin içeriğini elle düzeltmeyi sağlar. AddWordDialog'dan ayrıdır: oradaki
akış "terim gir → üret → kaydet" etrafında kuruludur, burada ise doğrudan alan
editörü vardır ve mevcut içerik düzenlenir.

Stiller global QSS'ten gelir; renk gömülmez.
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from lexis.domain.models import Word
from lexis.services.word_service import WordService
from lexis.ui.theme import repolish
from lexis.ui.widgets.common import SectionLabel

logger = logging.getLogger(__name__)

# Örnek cümleler "foreign\nturkish" olarak saklanır; editörde okunabilir olsun
# diye çift satırla ayrılıp gösterilir.
EXAMPLE_SEPARATOR = "\n\n"


def _join_examples(examples: list[str]) -> str:
    return EXAMPLE_SEPARATOR.join(examples)


def _split_examples(text: str) -> list[str]:
    return [block.strip() for block in text.split(EXAMPLE_SEPARATOR) if block.strip()]


def _join_list(items: list[str]) -> str:
    return ", ".join(items)


def _split_list(text: str) -> list[str]:
    return [part.strip() for part in text.split(",") if part.strip()]


class EditWordDialog(QDialog):
    """Kelime içeriğini elle düzenleme diyaloğu."""

    word_saved = pyqtSignal(str)  # word_id

    def __init__(self, word: Word, service: WordService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._word = word
        self._service = service
        self._setup_ui()
        self._populate()

    def _setup_ui(self) -> None:
        self.setWindowTitle(f"'{self._word.term}' düzenle")
        self.setModal(True)
        # AddWordDialog sabit boyutluydu ve büyük sistem fontlarında içeriği
        # kırpıyordu; bu diyalog yeniden boyutlanabilir.
        self.setMinimumSize(560, 560)
        self.resize(640, 720)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Başlık ──
        header = QWidget()
        header.setObjectName("dialogHeader")
        header.setFixedHeight(70)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(24, 0, 24, 0)

        title = QLabel("Kelimeyi Düzenle")
        title.setObjectName("dialogTitle")
        h_layout.addWidget(title, 1)

        close_btn = QPushButton("×")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(32, 32)
        close_btn.setToolTip("Kapat")
        close_btn.setAccessibleName("Kapat")
        close_btn.clicked.connect(self.reject)
        h_layout.addWidget(close_btn)
        root.addWidget(header)

        # ── Form ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        content = QWidget()
        content.setObjectName("dialogSurface")
        form = QVBoxLayout(content)
        form.setContentsMargins(24, 20, 24, 24)
        form.setSpacing(6)

        self._term_input = QLineEdit()
        self._term_input.setMinimumHeight(40)
        self._short_input = QLineEdit()
        self._short_input.setMinimumHeight(40)
        self._pos_input = QLineEdit()
        self._pos_input.setMinimumHeight(40)
        self._phonetic_input = QLineEdit()
        self._phonetic_input.setMinimumHeight(40)
        self._synonyms_input = QLineEdit()
        self._synonyms_input.setMinimumHeight(40)
        self._antonyms_input = QLineEdit()
        self._antonyms_input.setMinimumHeight(40)
        self._tags_input = QLineEdit()
        self._tags_input.setMinimumHeight(40)

        self._definition_input = QTextEdit()
        self._definition_input.setMinimumHeight(90)
        self._examples_input = QTextEdit()
        self._examples_input.setMinimumHeight(120)
        self._notes_input = QTextEdit()
        self._notes_input.setMinimumHeight(70)

        fields: list[tuple[str, QWidget, str]] = [
            ("KELİME", self._term_input, ""),
            ("KISA TANIM", self._short_input, ""),
            ("TANIM", self._definition_input, ""),
            ("SÖZCÜK TÜRÜ", self._pos_input, "İsim, Fiil, Sıfat..."),
            ("TELAFFUZ", self._phonetic_input, "/əˈfɛmərəl/"),
            ("EŞ ANLAMLILAR", self._synonyms_input, "virgülle ayırın"),
            ("ZIT ANLAMLILAR", self._antonyms_input, "virgülle ayırın"),
            (
                "ÖRNEK CÜMLELER",
                self._examples_input,
                "Her örnek boş satırla ayrılır. Çeviriyi alt satıra yazın.",
            ),
            ("KULLANIM NOTU", self._notes_input, ""),
            ("ETİKETLER", self._tags_input, "virgülle ayırın"),
        ]
        for label, widget, hint in fields:
            form.addWidget(SectionLabel(label))
            if hint:
                widget.setPlaceholderText(hint)  # QLineEdit ve QTextEdit'te aynı API
            widget.setAccessibleName(label.capitalize())
            form.addWidget(widget)
            form.addSpacing(10)

        form.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        # ── Alt bar ──
        footer = QWidget()
        footer.setObjectName("dialogFooter")
        footer.setFixedHeight(70)
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(24, 0, 24, 0)
        f_layout.setSpacing(12)

        self._status_label = QLabel("")
        self._status_label.setObjectName("statusText")
        f_layout.addWidget(self._status_label, 1)

        cancel_btn = QPushButton("İptal")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.setMinimumHeight(40)
        cancel_btn.clicked.connect(self.reject)
        f_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Kaydet")
        save_btn.setObjectName("primaryBtn")
        save_btn.setMinimumHeight(40)
        save_btn.setMinimumWidth(100)
        save_btn.clicked.connect(self._save)
        f_layout.addWidget(save_btn)

        root.addWidget(footer)

    def _populate(self) -> None:
        w = self._word
        self._term_input.setText(w.term)
        self._short_input.setText(w.definition_short)
        self._definition_input.setPlainText(w.definition)
        self._pos_input.setText(w.part_of_speech)
        self._phonetic_input.setText(w.phonetic)
        self._synonyms_input.setText(_join_list(w.synonyms))
        self._antonyms_input.setText(_join_list(w.antonyms))
        self._examples_input.setPlainText(_join_examples(w.example_sentences))
        self._notes_input.setPlainText(w.usage_notes)
        self._tags_input.setText(_join_list(w.tags))

    def _set_status(self, message: str, level: str = "error") -> None:
        self._status_label.setText(message)
        self._status_label.setProperty("level", level)
        repolish(self._status_label)

    def _save(self) -> None:
        term = self._term_input.text().strip()
        if not term:
            self._set_status("Kelime boş olamaz.")
            return

        w = self._word
        w.term = term
        w.definition_short = self._short_input.text().strip()
        w.definition = self._definition_input.toPlainText().strip()
        w.part_of_speech = self._pos_input.text().strip()
        w.phonetic = self._phonetic_input.text().strip()
        w.synonyms = _split_list(self._synonyms_input.text())
        w.antonyms = _split_list(self._antonyms_input.text())
        w.example_sentences = _split_examples(self._examples_input.toPlainText())
        w.usage_notes = self._notes_input.toPlainText().strip()
        w.tags = [t.lower() for t in _split_list(self._tags_input.text())]
        # Elle düzenlenen içerik artık AI üretimi sayılmaz.
        w.ai_generated = False

        try:
            self._service.update_word(w)
        except Exception as e:
            logger.exception("Kelime güncellenemedi: %s", w.id)
            self._set_status(f"Kaydedilemedi: {e}")
            return

        self.word_saved.emit(w.id)
        self.accept()
