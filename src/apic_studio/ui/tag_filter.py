from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
    QWidgetAction,
)

from apic_studio.services.tags import TagService

from .dialogs import ACCENT, DIALOG_STYLE

ACTIVE_STYLE = f"""
QToolButton {{background-color: {ACCENT}; color: #000; border-radius: 5px; padding: 0 8px}}
QToolButton::menu-indicator {{image: none}}
"""
IDLE_STYLE = """
QToolButton {border: 1px solid black; border-radius: 5px; padding: 0 8px}
QToolButton:hover {background-color: #505050}
QToolButton::menu-indicator {image: none}
"""


class _TagList(QListWidget):
    """Space / Enter toggle the current row, like clicking it."""

    toggle_requested = Signal(QListWidgetItem)

    def keyPressEvent(self, event: QKeyEvent):
        item = self.currentItem()
        if item is not None and event.key() in (
            Qt.Key.Key_Space.value,
            Qt.Key.Key_Return.value,
            Qt.Key.Key_Enter.value,
        ):
            self.toggle_requested.emit(item)
            return
        super().keyPressEvent(event)


class TagFilterPanel(QWidget):
    """The checklist inside the Tags popup."""

    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setStyleSheet(DIALOG_STYLE)
        self.setMinimumWidth(240)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Find a tag")
        self.search.setClearButtonEnabled(True)

        self.list = _TagList()
        self.list.setMaximumHeight(300)
        self.list.setSpacing(1)
        self.list.setSelectionMode(QListWidget.SelectionMode.NoSelection)

        self.empty = QLabel("No tags yet. Add some in the attribute editor.")
        self.empty.setObjectName("hint")
        self.empty.setWordWrap(True)

        self.match_all = QCheckBox("Match all selected tags")
        self.match_all.setChecked(True)
        self.match_all.setToolTip("Off: show assets with any of the selected tags")

        self.clear_btn = QPushButton("Clear")

        bottom = QHBoxLayout()
        bottom.addWidget(self.match_all)
        bottom.addStretch()
        bottom.addWidget(self.clear_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.search)
        layout.addWidget(self.list)
        layout.addWidget(self.empty)
        layout.addLayout(bottom)

        self.search.textChanged.connect(self.apply_search)
        # the items aren't user checkable, a click anywhere on the row toggles,
        # otherwise only the tiny indicator would
        self.list.itemClicked.connect(self.toggle)
        self.list.toggle_requested.connect(self.toggle)
        self.match_all.toggled.connect(self.changed)
        self.clear_btn.clicked.connect(self.clear)

    def populate(self, tags: list[str], selected: list[str]):
        self.list.clear()
        lowered = {t.lower() for t in selected}
        for tag in tags:
            item = QListWidgetItem(tag)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            checked = tag.lower() in lowered
            item.setCheckState(
                Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
            )
            self.list.addItem(item)

        self.list.setVisible(bool(tags))
        self.empty.setVisible(not tags)
        self.apply_search(self.search.text())

    def apply_search(self, text: str):
        text = text.strip().lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            item.setHidden(text not in item.text().lower())

    def toggle(self, item: QListWidgetItem):
        checked = item.checkState() == Qt.CheckState.Checked
        item.setCheckState(
            Qt.CheckState.Unchecked if checked else Qt.CheckState.Checked
        )
        self.changed.emit()

    def clear(self):
        for i in range(self.list.count()):
            self.list.item(i).setCheckState(Qt.CheckState.Unchecked)
        self.changed.emit()

    def selected(self) -> list[str]:
        items = (self.list.item(i) for i in range(self.list.count()))
        return [i.text() for i in items if i.checkState() == Qt.CheckState.Checked]


class TagFilterButton(QToolButton):
    """Toolbar button narrowing the pool to assets carrying the picked tags."""

    changed = Signal()

    def __init__(self, height: int = 30, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(height)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)

        self._selected: list[str] = []
        self._match_all = True

        self.panel = TagFilterPanel()
        action = QWidgetAction(self)
        action.setDefaultWidget(self.panel)
        self.popup = QMenu(self)
        self.popup.addAction(action)
        self.setMenu(self.popup)

        self.popup.aboutToShow.connect(self.refresh)
        self.panel.changed.connect(self.on_panel_changed)

        self.update_look()

    def selection(self) -> tuple[list[str], bool]:
        return list(self._selected), self._match_all

    def set_selected(self, tags: list[str]):
        if tags == self._selected:
            return
        self._selected = list(tags)
        self.update_look()
        self.changed.emit()

    def refresh(self):
        """Fill the panel from the tag table, the list may have changed."""
        tags = TagService().get_all()
        known = {t.lower() for t in tags}
        # keep showing a picked tag even if it vanished from the table
        tags += [t for t in self._selected if t.lower() not in known]
        self.panel.populate(tags, self._selected)
        self.panel.search.setFocus()

    def on_panel_changed(self):
        self._selected = self.panel.selected()
        self._match_all = self.panel.match_all.isChecked()
        self.update_look()
        self.changed.emit()

    def rename_tag(self, old: str, new: str | None):
        """Follow a tag that was renamed (or deleted, new=None) everywhere."""
        if old not in self._selected:
            return

        tags = [new if t == old else t for t in self._selected]
        self.set_selected([t for t in dict.fromkeys(tags) if t])

    def update_look(self):
        count = len(self._selected)
        self.setText(f"Tags ({count}) ▾" if count else "Tags ▾")
        self.setStyleSheet(ACTIVE_STYLE if count else IDLE_STYLE)

        if count:
            joiner = " and " if self._match_all else " or "
            self.setToolTip("Showing assets tagged " + joiner.join(self._selected))
        else:
            self.setToolTip("Filter by tags")
