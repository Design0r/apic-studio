from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QSizePolicy, QWidget


class Searchbar(QWidget):
    text_changed = Signal(str)

    def __init__(
        self,
        height: int = 30,
        max_width: int | None = 300,
        placeholder: str = "Search",
        delay_ms: int = 300,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._height = height
        self._max_width = max_width
        self._placeholder = placeholder
        self._delay_ms = delay_ms
        self._pending_text = ""

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

    def init_widgets(self):
        self.searchbar = QLineEdit()
        self.searchbar.setPlaceholderText(self._placeholder)
        self.searchbar.setFixedHeight(self._height)
        if self._max_width is not None:
            self.searchbar.setMaximumWidth(self._max_width)
        else:
            # take whatever room the surrounding layout leaves
            self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.searchbar.setClearButtonEnabled(True)
        self.searchbar.setToolTip("Search (Ctrl+F), Esc clears")
        self.searchbar.setStyleSheet(
            "border: 1px solid black;border-radius: 5px; padding-left: 4px"
        )

        # debounce timer
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._emit_debounced)

        # Every toolbar has its own searchbar, but only the one on screen is
        # visible, and shortcuts of hidden widgets don't fire
        self._focus_shortcut = QShortcut(
            QKeySequence(QKeySequence.StandardKey.Find),
            self,
            context=Qt.ShortcutContext.WindowShortcut,
        )
        self._clear_shortcut = QShortcut(
            QKeySequence(Qt.Key.Key_Escape),
            self.searchbar,
            context=Qt.ShortcutContext.WidgetShortcut,
        )

    def init_layouts(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.addWidget(self.searchbar)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

    def init_signals(self):
        # Fires only on user edits (not programmatic changes)
        self.searchbar.textEdited.connect(self._on_text_edited)

        # Optional: emit immediately on Enter or when editing finishes (focus out)
        self.searchbar.returnPressed.connect(self._emit_now)
        self.searchbar.editingFinished.connect(self._emit_now)

        # the clear button empties the field without a textEdited
        self.searchbar.textChanged.connect(lambda text: text or self._emit_now())

        self._focus_shortcut.activated.connect(self.focus_search)
        self._clear_shortcut.activated.connect(self.clear_search)

    def focus_search(self):
        self.searchbar.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.searchbar.selectAll()

    def clear_search(self):
        self.searchbar.clear()
        self.searchbar.clearFocus()

    # --- internals ---

    def _on_text_edited(self, text: str):
        self._pending_text = text
        self._debounce_timer.start(self._delay_ms)

    def _emit_debounced(self):
        self.text_changed.emit(self._pending_text)

    def _emit_now(self):
        # If timer is running, stop and emit current text right away
        if self._debounce_timer.isActive():
            self._debounce_timer.stop()
        current = self.searchbar.text()
        self._pending_text = current
        self.text_changed.emit(current)
