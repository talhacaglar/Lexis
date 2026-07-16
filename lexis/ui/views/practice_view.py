"""
Lexis — View: Practice (Aralıklı Tekrar)

Tekrar zamanı gelmiş kelimelerle flashcard tarzı çalışma oturumu.
Kullanıcı kelimeyi hatırlamaya çalışır, cevabı açar ve kendini
Tekrar / Zor / İyi / Kolay olarak değerlendirir (SM-2).
"""

from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from lexis.domain.models import ReviewGrade, Word
from lexis.services.word_service import WordService
from lexis.ui.widgets.common import Divider

logger = logging.getLogger(__name__)


class PracticeView(QWidget):
    """Aralıklı tekrar çalışma oturumu görünümü."""

    back_requested = pyqtSignal()
    session_finished = pyqtSignal()  # dashboard/kütüphane yenilensin
    error_occurred = pyqtSignal(str)  # MainWindow toast gösterir

    def __init__(self, word_service: WordService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = word_service
        self._queue: list[Word] = []
        self._index = 0
        self._reviewed = 0
        self._revealed = False
        self._setup_ui()

    # ── UI kurulumu ───────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Üst bar: geri + ilerleme
        topbar = QWidget()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(72)
        tb = QHBoxLayout(topbar)
        tb.setContentsMargins(36, 0, 36, 0)

        back_btn = QPushButton("←  Geri")
        back_btn.setObjectName("secondaryBtn")
        back_btn.setFixedHeight(38)
        back_btn.clicked.connect(self.back_requested)
        tb.addWidget(back_btn)
        tb.addStretch()

        self._progress_label = QLabel("")
        self._progress_label.setObjectName("practiceProgress")
        tb.addWidget(self._progress_label)
        root.addWidget(topbar)

        # İçerik (kaydırılabilir)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        outer = QVBoxLayout(content)
        outer.setContentsMargins(36, 12, 36, 36)
        outer.setSpacing(0)
        outer.addStretch()

        # Kart
        self._card = QFrame()
        self._card.setObjectName("card")
        self._card.setMinimumHeight(360)
        self._card.setMaximumWidth(640)
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(40, 36, 40, 36)
        card_layout.setSpacing(18)

        self._term_label = QLabel("")
        self._term_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._term_label.setWordWrap(True)
        self._term_label.setObjectName("practiceTerm")
        card_layout.addWidget(self._term_label)

        self._meta_label = QLabel("")
        self._meta_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._meta_label.setObjectName("practiceMeta")
        card_layout.addWidget(self._meta_label)

        # Cevap bölümü (açılınca görünür)
        self._answer_widget = QWidget()
        ans = QVBoxLayout(self._answer_widget)
        ans.setContentsMargins(0, 8, 0, 0)
        ans.setSpacing(12)

        ans.addWidget(Divider())

        self._definition_label = QLabel("")
        self._definition_label.setWordWrap(True)
        self._definition_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._definition_label.setObjectName("practiceDefinition")
        ans.addWidget(self._definition_label)

        self._examples_label = QLabel("")
        self._examples_label.setWordWrap(True)
        self._examples_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._examples_label.setObjectName("practiceExamples")
        ans.addWidget(self._examples_label)

        card_layout.addWidget(self._answer_widget)
        card_layout.addStretch()

        # Kartı yatayda ortala
        card_row = QHBoxLayout()
        card_row.addStretch()
        card_row.addWidget(self._card)
        card_row.addStretch()
        outer.addLayout(card_row)

        # Aksiyon butonları
        self._action_row = QHBoxLayout()
        self._action_row.setSpacing(12)
        self._action_row.setContentsMargins(0, 24, 0, 0)
        action_wrap = QHBoxLayout()
        action_wrap.addStretch()
        self._action_container = QWidget()
        self._action_container.setMaximumWidth(640)
        self._action_container.setLayout(self._action_row)
        action_wrap.addWidget(self._action_container)
        action_wrap.addStretch()
        outer.addLayout(action_wrap)

        # "Cevabı Göster" butonu
        self._reveal_btn = QPushButton("Cevabı Göster  (Boşluk)")
        self._reveal_btn.setObjectName("primaryBtn")
        self._reveal_btn.setMinimumHeight(48)
        self._reveal_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._reveal_btn.clicked.connect(self._reveal)

        # Derecelendirme butonları
        self._grade_buttons: list[QPushButton] = []
        for i, grade in enumerate(
            [ReviewGrade.AGAIN, ReviewGrade.HARD, ReviewGrade.GOOD, ReviewGrade.EASY],
            start=1,
        ):
            btn = QPushButton(f"{grade.display_name}  ({i})")
            btn.setObjectName("gradeBtn")
            btn.setProperty("grade", grade.name.lower())
            btn.setMinimumHeight(48)
            # Odak view'da kalsın: aksi hâlde değerlendirmeden sonra Boşluk tuşu
            # keyPressEvent yerine odaklanmış butonu tetikler.
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.clicked.connect(lambda _=False, g=grade: self._grade(g))
            self._grade_buttons.append(btn)

        # Tamamlanma ekranı
        self._done_label = QLabel("")
        self._done_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._done_label.setWordWrap(True)
        self._done_label.setObjectName("practiceDone")
        self._done_label.setVisible(False)
        outer.addWidget(self._done_label)

        outer.addStretch()
        scroll.setWidget(content)
        root.addWidget(scroll, 1)

    # ── Oturum yönetimi ───────────────────────────────────────────────────

    def start_session(self, limit: int = 30) -> None:
        """Yeni bir tekrar oturumu başlatır."""
        self._queue = self._service.get_due_words(limit=limit)
        self._index = 0
        self._reviewed = 0
        self.setFocus()
        if not self._queue:
            self._show_done(empty=True)
        else:
            self._show_current()

    def _current_word(self) -> Word | None:
        if 0 <= self._index < len(self._queue):
            return self._queue[self._index]
        return None

    def _show_current(self) -> None:
        word = self._current_word()
        if word is None:
            self._show_done()
            return

        self._revealed = False
        self._card.setVisible(True)
        self._done_label.setVisible(False)
        self._answer_widget.setVisible(False)

        self._progress_label.setText(f"{self._index + 1} / {len(self._queue)}")
        self._term_label.setText(word.term)
        meta = word.language_display
        if word.part_of_speech:
            meta += f"  ·  {word.part_of_speech}"
        self._meta_label.setText(meta)

        self._definition_label.setText(word.definition or word.definition_short or "—")
        self._examples_label.setText(self._format_examples(word))

        self._show_reveal_button()

    @staticmethod
    def _format_examples(word: Word, limit: int = 2) -> str:
        lines: list[str] = []
        for ex in word.example_sentences[:limit]:
            lines.append(ex.replace("\n", "  —  "))
        return "\n".join(lines)

    def _clear_actions(self) -> None:
        while self._action_row.count():
            item = self._action_row.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)

    def _show_reveal_button(self) -> None:
        self._clear_actions()
        self._action_row.addWidget(self._reveal_btn)
        self._reveal_btn.setVisible(True)

    def _show_grade_buttons(self) -> None:
        self._clear_actions()
        self._reveal_btn.setVisible(False)
        for btn in self._grade_buttons:
            self._action_row.addWidget(btn)
            btn.setVisible(True)

    def _reveal(self) -> None:
        if self._current_word() is None or self._revealed:
            return
        self._revealed = True
        self._answer_widget.setVisible(True)
        self._show_grade_buttons()

    def _grade(self, grade: ReviewGrade) -> None:
        word = self._current_word()
        if word is None or not self._revealed:
            return
        try:
            self._service.review_word(word.id, grade)
        except Exception:
            # Kaydedilemeyen değerlendirmede karta ilerlemek tekrarı sessizce
            # kaybettirirdi; kullanıcı uyarılır ve kart yerinde kalır.
            logger.exception("Değerlendirme kaydedilemedi: %s", word.id)
            self.error_occurred.emit(
                f"'{word.term}' için değerlendirme kaydedilemedi. Tekrar deneyin."
            )
            return

        self._reviewed += 1
        self._index += 1
        self._show_current()

    def _show_done(self, empty: bool = False) -> None:
        self._card.setVisible(False)
        self._clear_actions()
        self._progress_label.setText("")
        if empty and self._reviewed == 0:
            self._done_label.setText(
                "🎉 Tekrar edilecek kelime yok!\n\n"
                "Tüm kelimelerin güncel. Yeni kelimeler ekledikçe ya da tekrar\n"
                "zamanları geldikçe burada görünecekler."
            )
        else:
            self._done_label.setText(
                f"✅ Oturum tamamlandı!\n\n{self._reviewed} kelime çalışıldı.\n\n"
                "Düzenli tekrar, kalıcı öğrenmenin anahtarıdır."
            )
        self._done_label.setVisible(True)
        if self._reviewed > 0:
            self.session_finished.emit()

    # ── Klavye kısayolları ────────────────────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if not self._revealed:
            if key in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._reveal()
                return
        else:
            grade_map = {
                Qt.Key.Key_1: ReviewGrade.AGAIN,
                Qt.Key.Key_2: ReviewGrade.HARD,
                Qt.Key.Key_3: ReviewGrade.GOOD,
                Qt.Key.Key_4: ReviewGrade.EASY,
                Qt.Key.Key_Space: ReviewGrade.GOOD,
            }
            if key in grade_map:
                self._grade(grade_map[key])
                return
        super().keyPressEvent(event)
