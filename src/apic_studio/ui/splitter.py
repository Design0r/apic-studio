from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QSplitter, QSplitterHandle, QWidget

SPLITTER_STYLE = """
QSplitter::handle {background-color: #3a3a3a}
QSplitter::handle:hover {background-color: rgb(235, 177, 52)}
QSplitter::handle:pressed {background-color: rgb(235, 177, 52)}
"""


class _PanelHandle(QSplitterHandle):
    def __init__(self, orientation: Qt.Orientation, parent: QSplitter):
        super().__init__(orientation, parent)
        # the stylesheet's :hover needs hover events, handles don't get them
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setToolTip("Drag to resize, double click to hide or show the details")

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        splitter = self.splitter()
        if isinstance(splitter, PanelSplitter):
            splitter.toggle_panel()


class PanelSplitter(QSplitter):
    """A main widget on the left and a side panel on the right that folds away.

    The main widget takes all extra room when the window resizes, the panel
    keeps its width. Folding remembers the width, so unfolding restores it.
    """

    panel_toggled = Signal(bool)

    HANDLE_WIDTH = 6

    def __init__(self, main: QWidget, panel: QWidget, parent: QWidget | None = None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setOpaqueResize(True)
        self.setHandleWidth(self.HANDLE_WIDTH)
        self.setStyleSheet(SPLITTER_STYLE)

        self.addWidget(main)
        self.addWidget(panel)
        self.setStretchFactor(0, 1)
        self.setStretchFactor(1, 0)

        # only the panel may be dragged shut, the asset view always stays
        self.setCollapsible(0, False)
        self.setCollapsible(1, True)

        self._panel_width = panel.sizeHint().width()
        self._was_open = True
        self.splitterMoved.connect(self._on_moved)

    def createHandle(self) -> QSplitterHandle:
        return _PanelHandle(self.orientation(), self)

    @property
    def panel_width(self) -> int:
        """The panel's width, or the one it gets back when it unfolds."""
        return self._panel_width

    def is_panel_open(self) -> bool:
        return self.sizes()[1] > 0

    def set_panel(self, open: bool, width: int | None = None):
        if width:
            self._panel_width = max(width, self.widget(1).minimumSizeHint().width())

        total = sum(self.sizes()) or self.width()
        panel = self._panel_width if open else 0
        self.setSizes([max(0, total - panel), panel])
        self._notify()

    def toggle_panel(self):
        self.set_panel(not self.is_panel_open())

    def _on_moved(self, pos: int, index: int):
        width = self.sizes()[1]
        if width > 0:
            self._panel_width = width
        self._notify()

    def _notify(self):
        is_open = self.is_panel_open()
        if is_open != self._was_open:
            self._was_open = is_open
            self.panel_toggled.emit(is_open)
