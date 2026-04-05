"""
Lexis — Widget: Add Word Dialog

Yeni kelime ekleme ve AI içerik üretimi diyalogu.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from lexis.domain.models import SUPPORTED_LANGUAGES
from lexis.services.word_service import WordService
from lexis.ui.theme import Colors
from lexis.ui.widgets.loading_overlay import LoadingOverlay
from lexis.workers.ai_worker import AIGenerationWorker


class SectionLabel(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            color: {Colors.TEXT_MUTED};
            font-size: 10px;
            font-weight: 700;
            letter-spacing: 1px;
        """)


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
        self._ai_worker: AIGenerationWorker | None = None
        self._ai_data: dict | None = None

        self._setup_ui()
        self._setup_connections()

    def _setup_ui(self) -> None:
        self.setWindowTitle("Yeni Kelime Ekle")
        self.setFixedSize(560, 680)
        self.setModal(True)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.BG_SURFACE};
                border-radius: 16px;
            }}
            QPushButton#secondaryBtn {{
                background: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 10px;
                font-size: 13px;
            }}
            QPushButton#secondaryBtn:hover {{
                background: {Colors.BG_HOVER};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER_FOCUS};
            }}
            QPushButton#primaryBtn {{
                background: {Colors.ACCENT};
                color: white;
                border-radius: 10px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton#primaryBtn:disabled {{
                background: {Colors.BG_ELEVATED};
                color: {Colors.TEXT_MUTED};
            }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──
        header = QWidget()
        header.setFixedHeight(70)
        header.setStyleSheet(f"""
            background-color: {Colors.BG_ELEVATED};
            border-bottom: 1px solid {Colors.BORDER_SUBTLE};
            border-top-left-radius: 16px;
            border-top-right-radius: 16px;
        """)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(24, 0, 24, 0)

        title = QLabel("Yeni Kelime Ekle")
        title.setStyleSheet(f"""
            color: {Colors.TEXT_PRIMARY};
            font-size: 16px;
            font-weight: 700;
        """)

        close_btn = QPushButton("×")
        close_btn.setFixedSize(32, 32)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {Colors.TEXT_MUTED};
                font-size: 20px;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background: {Colors.BG_HOVER};
                color: {Colors.TEXT_PRIMARY};
            }}
        """)
        close_btn.clicked.connect(self.reject)

        h_layout.addWidget(title, 1)
        h_layout.addWidget(close_btn)
        root.addWidget(header)

        # ── Scrollable Content ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        content = QWidget()
        content.setStyleSheet(f"background: {Colors.BG_SURFACE};")
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
        self._generate_btn = QPushButton("  ✨  AI ile İçerik Üret")
        self._generate_btn.setObjectName("primaryBtn")
        self._generate_btn.setMinimumHeight(44)
        self._generate_btn.setEnabled(False)
        form.addWidget(self._generate_btn)

        # ── AI Result Fields ──
        self._result_widget = QWidget()
        self._result_widget.setVisible(False)
        result_layout = QVBoxLayout(self._result_widget)
        result_layout.setContentsMargins(0, 0, 0, 0)
        result_layout.setSpacing(16)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background: {Colors.BORDER_SUBTLE}; max-height: 1px;")
        result_layout.addWidget(sep)

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
        footer.setFixedHeight(70)
        footer.setStyleSheet(f"""
            background-color: {Colors.BG_ELEVATED};
            border-top: 1px solid {Colors.BORDER_SUBTLE};
            border-bottom-left-radius: 16px;
            border-bottom-right-radius: 16px;
        """)
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(24, 0, 24, 0)
        f_layout.setSpacing(12)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px;")
        f_layout.addWidget(self._status_label, 1)

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

    def _on_term_changed(self, text: str) -> None:
        has_text = bool(text.strip())
        self._generate_btn.setEnabled(has_text)

    def _generate_ai_content(self) -> None:
        term = self._term_input.text().strip()
        if not term:
            return

        lang_code = self._lang_combo.currentData()
        self._loading.show_loading(f"'{term}' için içerik üretiliyor...")
        self._generate_btn.setEnabled(False)

        from lexis.services.ai_service import AIService
        ai_service = self._service._ai

        self._ai_worker = AIGenerationWorker(ai_service, term, lang_code, parent=self)
        self._ai_worker.finished.connect(self._on_ai_finished)
        self._ai_worker.error.connect(self._on_ai_error)
        self._ai_worker.start()

    def _on_ai_finished(self, data: dict) -> None:
        self._loading.hide_loading()
        self._ai_data = data
        self._populate_fields(data)
        self._result_widget.setVisible(True)
        self._save_btn.setEnabled(True)
        self._generate_btn.setEnabled(True)
        self._status_label.setText("✓ İçerik üretildi")
        self._status_label.setStyleSheet(f"color: {Colors.STATUS_LEARNED}; font-size: 12px; font-weight: 600;")

    def _on_ai_error(self, message: str) -> None:
        self._loading.hide_loading()
        self._generate_btn.setEnabled(True)
        self._status_label.setText(f"Hata: {message}")
        self._status_label.setStyleSheet(f"color: {Colors.ERROR}; font-size: 12px;")
        # Hata olsa bile kaydetmeye izin ver (boş veriyle)
        self._result_widget.setVisible(True)
        self._save_btn.setEnabled(True)

    def _populate_fields(self, data: dict) -> None:
        self._short_def.setText(data.get("definition_short", ""))
        self._definition.setPlainText(data.get("definition", ""))
        self._pos_input.setText(data.get("part_of_speech", ""))
        self._synonyms_input.setText(", ".join(data.get("synonyms", [])))
        self._antonyms_input.setText(", ".join(data.get("antonyms", [])))
        self._examples_input.setPlainText("\n".join(data.get("example_sentences", [])))
        self._usage_notes.setPlainText(data.get("usage_notes", ""))

    def _collect_ai_data(self) -> dict:
        """Formdan güncel AI verisini toplar."""
        synonyms = [s.strip() for s in self._synonyms_input.text().split(",") if s.strip()]
        antonyms = [a.strip() for a in self._antonyms_input.text().split(",") if a.strip()]
        examples = [e.strip() for e in self._examples_input.toPlainText().splitlines() if e.strip()]

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
            self._status_label.setText(str(e))
            self._status_label.setStyleSheet(f"color: {Colors.ERROR}; font-size: 12px;")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._loading.resize(self.size())
