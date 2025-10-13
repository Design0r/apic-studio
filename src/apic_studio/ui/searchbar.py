from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QWidget


class Searchbar(QWidget):
    text_changed = Signal(str)

    def __init__(
        self,
        height: int = 30,
        max_width: int = 300,
        placeholder: str = "  Search",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._height = height
        self._max_width = max_width
        self._placeholder = placeholder

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

    def init_widgets(self):
        self.searchbar = QLineEdit()
        self.searchbar.setPlaceholderText(self._placeholder)
        self.searchbar.setFixedHeight(self._height)
        self.searchbar.setMaximumWidth(self._max_width)
        self.searchbar.setStyleSheet("border: 1px solid black;border-radius: 5px")

    def init_layouts(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.addWidget(self.searchbar)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

    def init_signals(self):
        self.searchbar.textChanged.connect(self.text_changed.emit)
