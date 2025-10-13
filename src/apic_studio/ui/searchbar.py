from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QWidget


class Searchbar(QWidget):
    text_changed = Signal(str)

    def __init__(
        self,
        height: int = 30,
        max_width: int = 300,
        placeholder: str = "  Search",
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
        self.searchbar.setMaximumWidth(self._max_width)
        self.searchbar.setStyleSheet("border: 1px solid black;border-radius: 5px")

        # debounce timer
        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._emit_debounced)

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
