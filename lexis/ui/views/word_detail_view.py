"""
Lexis — View: Word Detail

Tek kelime için tam içerik ekranı.
Tanım, eş/zıt anlamlılar, örnek cümleler, durum yönetimi.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from lexis.domain.models import Word, WordStatus
from lexis.services.word_service import WordService
from lexis.ui.theme import repolish
from lexis.ui.widgets.common import Chip, Divider, SectionLabel, StatusBadge
from lexis.ui.widgets.loading_overlay import LoadingOverlay
from lexis.ui.widgets.tag_badge import TagBadge
from lexis.workers.ai_worker import AIGenerationWorker


class WordDetailView(QWidget):
    """
    Kelime detay ekranı.
    Sidebar navigasyonu yerine inline stack navigation kullanır.
    """

    back_requested = pyqtSignal()
    word_deleted = pyqtSignal(str)    # word_id
    word_updated = pyqtSignal(str)    # word_id

    def __init__(self, word_service: WordService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = word_service
        self._word: Word | None = None
        self._ai_worker: AIGenerationWorker | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top Navigation Bar ──
        navbar = QWidget()
        navbar.setObjectName("detailNavbar")
        navbar.setFixedHeight(60)
        nav_layout = QHBoxLayout(navbar)
        nav_layout.setContentsMargins(24, 0, 24, 0)
        nav_layout.setSpacing(12)

        back_btn = QPushButton("← Geri")
        back_btn.setObjectName("secondaryBtn")
        back_btn.setFixedHeight(34)
        back_btn.clicked.connect(self.back_requested)
        nav_layout.addWidget(back_btn)
        nav_layout.addStretch()

        self._regen_btn = QPushButton("✨ AI ile Yenile")
        self._regen_btn.setObjectName("secondaryBtn")
        self._regen_btn.setFixedHeight(34)
        self._regen_btn.clicked.connect(self._regenerate_ai)
        nav_layout.addWidget(self._regen_btn)

        self._delete_btn = QPushButton("🗑 Sil")
        self._delete_btn.setObjectName("dangerBtn")
        self._delete_btn.setFixedHeight(34)
        self._delete_btn.clicked.connect(self._delete_word)
        nav_layout.addWidget(self._delete_btn)

        root.addWidget(navbar)

        # ── Scrollable Content ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._content = QWidget()
        self._content.setObjectName("contentSurface")
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(60, 40, 60, 60)
        content_layout.setSpacing(0)

        # ── Word Header ──
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 32)
        header_layout.setSpacing(12)

        # Term + Favorite row
        term_row = QHBoxLayout()

        self._term_label = QLabel()
        self._term_label.setObjectName("detailTerm")
        term_row.addWidget(self._term_label, 1)

        self._fav_btn = QPushButton("♥")
        self._fav_btn.setObjectName("favoriteBtn")
        self._fav_btn.setProperty("size", "large")
        self._fav_btn.setFixedSize(44, 44)
        self._fav_btn.setToolTip("Favorilere ekle/çıkar")
        self._fav_btn.setAccessibleName("Favorilere ekle/çıkar")
        self._fav_btn.clicked.connect(self._toggle_favorite)
        term_row.addWidget(self._fav_btn)

        header_layout.addLayout(term_row)

        # Badges row: language + POS + status
        self._badges_row = QHBoxLayout()
        self._badges_row.setSpacing(8)
        self._lang_badge = QLabel()
        self._lang_badge.setObjectName("detailLangBadge")
        self._pos_badge = QLabel()
        self._pos_badge.setObjectName("detailPosBadge")
        self._status_badge = StatusBadge("new", "")
        self._badges_row.addWidget(self._lang_badge)
        self._badges_row.addWidget(self._pos_badge)
        self._badges_row.addWidget(self._status_badge)
        self._badges_row.addStretch()
        header_layout.addLayout(self._badges_row)

        content_layout.addWidget(header)
        content_layout.addWidget(Divider())

        # ── Definition ──
        def_section = QWidget()
        def_layout = QVBoxLayout(def_section)
        def_layout.setContentsMargins(0, 28, 0, 28)
        def_layout.setSpacing(12)

        self._short_def_label = QLabel()
        self._short_def_label.setObjectName("detailShortDef")
        self._short_def_label.setWordWrap(True)

        self._definition_label = QLabel()
        self._definition_label.setObjectName("detailDefinition")
        self._definition_label.setWordWrap(True)

        def_layout.addWidget(self._short_def_label)
        def_layout.addWidget(self._definition_label)

        content_layout.addWidget(def_section)
        content_layout.addWidget(Divider())

        # ── Status Selector ──
        status_section = QWidget()
        status_layout = QVBoxLayout(status_section)
        status_layout.setContentsMargins(0, 24, 0, 24)
        status_layout.setSpacing(12)

        status_title = SectionLabel("ÖĞRENME DURUMU")
        status_layout.addWidget(status_title)

        status_btns_row = QHBoxLayout()
        status_btns_row.setSpacing(8)
        self._status_btns: dict[str, QPushButton] = {}
        for ws in WordStatus:
            btn = QPushButton(f"{ws.icon}  {ws.display_name}")
            btn.setObjectName("filterChip")
            btn.clicked.connect(lambda _, s=ws: self._update_status(s))
            self._status_btns[ws.value] = btn
            status_btns_row.addWidget(btn)
        status_btns_row.addStretch()
        status_layout.addLayout(status_btns_row)

        content_layout.addWidget(status_section)
        content_layout.addWidget(Divider())

        # ── Synonyms & Antonyms ──
        syn_ant_section = QWidget()
        syn_ant_layout = QVBoxLayout(syn_ant_section)
        syn_ant_layout.setContentsMargins(0, 24, 0, 24)
        syn_ant_layout.setSpacing(16)

        # Synonyms
        syn_col = QVBoxLayout()
        syn_title = SectionLabel("EŞ ANLAMLILAR")
        syn_col.addWidget(syn_title)
        self._synonyms_row = QHBoxLayout()
        self._synonyms_row.setSpacing(6)
        self._synonyms_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        syn_col.addLayout(self._synonyms_row)
        syn_ant_layout.addLayout(syn_col)

        # Antonyms
        ant_col = QVBoxLayout()
        ant_title = SectionLabel("ZIT ANLAMLILAR")
        ant_col.addWidget(ant_title)
        self._antonyms_row = QHBoxLayout()
        self._antonyms_row.setSpacing(6)
        self._antonyms_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        ant_col.addLayout(self._antonyms_row)
        syn_ant_layout.addLayout(ant_col)

        content_layout.addWidget(syn_ant_section)
        content_layout.addWidget(Divider())

        # ── Example Sentences ──
        examples_section = QWidget()
        examples_layout = QVBoxLayout(examples_section)
        examples_layout.setContentsMargins(0, 24, 0, 24)
        examples_layout.setSpacing(12)

        ex_title = SectionLabel("ÖRNEK CÜMLELER")
        examples_layout.addWidget(ex_title)

        self._examples_container = QVBoxLayout()
        self._examples_container.setSpacing(10)
        examples_layout.addLayout(self._examples_container)

        content_layout.addWidget(examples_section)
        content_layout.addWidget(Divider())

        # ── Usage Notes ──
        usage_section = QWidget()
        usage_layout = QVBoxLayout(usage_section)
        usage_layout.setContentsMargins(0, 24, 0, 24)
        usage_layout.setSpacing(12)

        usage_title = SectionLabel("KULLANIM NOTU")
        self._usage_label = QLabel()
        self._usage_label.setObjectName("detailUsage")
        self._usage_label.setWordWrap(True)
        usage_layout.addWidget(usage_title)
        usage_layout.addWidget(self._usage_label)

        self._usage_section_widget = usage_section
        content_layout.addWidget(usage_section)
        content_layout.addWidget(Divider())

        # ── Tags ──
        tags_section = QWidget()
        tags_layout = QVBoxLayout(tags_section)
        tags_layout.setContentsMargins(0, 24, 0, 24)
        tags_layout.setSpacing(12)

        tags_title_row = QHBoxLayout()
        tags_title = SectionLabel("ETİKETLER")
        tags_title_row.addWidget(tags_title)
        tags_title_row.addStretch()

        tags_layout.addLayout(tags_title_row)

        self._tags_row = QHBoxLayout()
        self._tags_row.setSpacing(6)
        self._tags_row.setAlignment(Qt.AlignmentFlag.AlignLeft)
        tags_layout.addLayout(self._tags_row)

        # Quick tag add
        tag_add_row = QHBoxLayout()
        from PyQt6.QtWidgets import QLineEdit
        self._tag_input = QLineEdit()
        self._tag_input.setPlaceholderText("Etiket ekle...")
        self._tag_input.setFixedHeight(34)
        self._tag_input.setMaximumWidth(200)
        self._tag_input.returnPressed.connect(self._add_tag)

        tag_add_btn = QPushButton("Ekle")
        tag_add_btn.setObjectName("secondaryBtn")
        tag_add_btn.setFixedHeight(34)
        tag_add_btn.clicked.connect(self._add_tag)

        tag_add_row.addWidget(self._tag_input)
        tag_add_row.addWidget(tag_add_btn)
        tag_add_row.addStretch()
        tags_layout.addLayout(tag_add_row)

        content_layout.addWidget(tags_section)
        content_layout.addStretch()

        scroll.setWidget(self._content)
        root.addWidget(scroll, 1)

        # ── Loading Overlay ──
        self._loading = LoadingOverlay(self, "İçerik yenileniyor...")

    def load_word(self, word_id: str) -> None:
        """Belirtilen kelimeyi yükler ve görünümü günceller."""
        try:
            word = self._service.get_by_id(word_id)
            self._word = word
            self._render_word()
        except Exception:
            pass

    def _render_word(self) -> None:
        if not self._word:
            return
        w = self._word

        self._term_label.setText(w.term)

        # Favorite
        self._fav_btn.setProperty("active", "true" if w.is_favorite else "false")
        repolish(self._fav_btn)

        # Badges
        self._lang_badge.setText(w.language_display)
        self._pos_badge.setText(w.part_of_speech or "")
        self._status_badge.set_status(w.status.value, w.status.display_name)
        self._status_badge.setText(f"{w.status.icon}  {w.status.display_name}")

        # Status buttons
        for status_val, btn in self._status_btns.items():
            active = status_val == w.status.value
            btn.setProperty("active", "true" if active else "false")
            btn.setStyle(btn.style())

        # Definition
        self._short_def_label.setText(w.definition_short if w.definition_short else "")
        self._short_def_label.setVisible(bool(w.definition_short))
        self._definition_label.setText(w.definition)

        # Synonyms
        self._clear_layout(self._synonyms_row)
        for syn in w.synonyms[:8]:
            self._synonyms_row.addWidget(Chip(syn, variant="accent"))
        if not w.synonyms:
            self._synonyms_row.addWidget(self._empty_placeholder())

        # Antonyms
        self._clear_layout(self._antonyms_row)
        for ant in w.antonyms[:6]:
            self._antonyms_row.addWidget(Chip(ant, variant="danger"))
        if not w.antonyms:
            self._antonyms_row.addWidget(self._empty_placeholder())

        # Examples
        self._clear_layout(self._examples_container)
        for i, ex in enumerate(w.example_sentences, 1):
            ex_widget = QWidget()
            ex_widget.setObjectName("exampleCard")
            ex_widget.setStyleSheet("""
                QWidget#exampleCard {
                    background: transparent;
                    border: none;
                }
            """)
            ex_layout = QHBoxLayout(ex_widget)
            ex_layout.setContentsMargins(0, 12, 0, 12)
            ex_layout.setSpacing(12)

            num = QLabel(str(i))
            num.setObjectName("exampleNumber")

            text_layout = QVBoxLayout()
            text_layout.setSpacing(10)
            text_layout.setContentsMargins(0, 0, 0, 0)

            parts = ex.split('\n', 1)

            foreign_lbl = QLabel(parts[0].strip())
            foreign_lbl.setWordWrap(True)
            foreign_lbl.setObjectName("exampleForeign")
            text_layout.addWidget(foreign_lbl)

            if len(parts) > 1 and parts[1].strip():
                tr_lbl = QLabel(parts[1].strip())
                tr_lbl.setWordWrap(True)
                tr_lbl.setObjectName("exampleTranslation")
                text_layout.addWidget(tr_lbl)

            ex_layout.addWidget(num, 0, Qt.AlignmentFlag.AlignTop)
            ex_layout.addLayout(text_layout, 1)
            self._examples_container.addWidget(ex_widget)

        # Usage notes
        self._usage_label.setText(w.usage_notes or "")
        self._usage_section_widget.setVisible(bool(w.usage_notes))

        # Tags
        self._render_tags()

    def _render_tags(self) -> None:
        if not self._word:
            return
        self._clear_layout(self._tags_row)
        for tag in self._word.tags:
            badge = TagBadge(tag, removable=True)
            badge.remove_requested.connect(self._remove_tag)
            self._tags_row.addWidget(badge)

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    @staticmethod
    def _empty_placeholder() -> QLabel:
        """Boş liste yerine gösterilen tire."""
        lbl = QLabel("—")
        lbl.setObjectName("mutedText")
        return lbl

    def _toggle_favorite(self) -> None:
        if not self._word:
            return
        self._word = self._service.toggle_favorite(self._word.id)
        self._fav_btn.setProperty("active", "true" if self._word.is_favorite else "false")
        self._fav_btn.setStyle(self._fav_btn.style())
        self.word_updated.emit(self._word.id)

    def _update_status(self, status: WordStatus) -> None:
        if not self._word:
            return
        self._word = self._service.update_status(self._word.id, status)
        self._render_word()
        self.word_updated.emit(self._word.id)

    def _add_tag(self) -> None:
        if not self._word:
            return
        tag = self._tag_input.text().strip().lower()
        if tag:
            self._word = self._service.add_tag(self._word.id, tag)
            self._tag_input.clear()
            self._render_tags()
            self.word_updated.emit(self._word.id)

    def _remove_tag(self, tag: str) -> None:
        if not self._word:
            return
        self._word = self._service.remove_tag(self._word.id, tag)
        self._render_tags()
        self.word_updated.emit(self._word.id)

    def _delete_word(self) -> None:
        if not self._word:
            return
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Kelimeyi Sil",
            f"'{self._word.term}' kelimesini silmek istediğinizden emin misiniz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            word_id = self._word.id
            self._service.delete_word(word_id)
            self.word_deleted.emit(word_id)
            self.back_requested.emit()

    def _regenerate_ai(self) -> None:
        if not self._word:
            return
        if not self._service.ai_configured:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "API Anahtarı Yok", "Lütfen Ayarlar'dan Gemini API anahtarınızı girin.")
            return

        self._loading.show_loading(f"'{self._word.term}' için içerik yenileniyor...")
        self._regen_btn.setEnabled(False)

        self._ai_worker = AIGenerationWorker(
            self._service._ai,
            self._word.term,
            self._word.language,
            parent=self,
        )
        self._ai_worker.finished.connect(self._on_regen_finished)
        self._ai_worker.error.connect(self._on_regen_error)
        self._ai_worker.start()

    def _on_regen_finished(self, data: dict) -> None:
        self._loading.hide_loading()
        self._regen_btn.setEnabled(True)
        if self._word:
            self._word.definition = data.get("definition", self._word.definition)
            self._word.definition_short = data.get("definition_short", self._word.definition_short)
            self._word.part_of_speech = data.get("part_of_speech", self._word.part_of_speech)
            self._word.synonyms = data.get("synonyms", self._word.synonyms)
            self._word.antonyms = data.get("antonyms", self._word.antonyms)
            self._word.example_sentences = data.get("example_sentences", self._word.example_sentences)
            self._word.usage_notes = data.get("usage_notes", self._word.usage_notes)
            self._word.ai_generated = True
            self._word = self._service.update_word(self._word)
            self._render_word()
            self.word_updated.emit(self._word.id)

    def _on_regen_error(self, message: str) -> None:
        self._loading.hide_loading()
        self._regen_btn.setEnabled(True)
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.warning(self, "Hata", f"İçerik yenilenemedi:\n{message}")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._loading.resize(self.size())
