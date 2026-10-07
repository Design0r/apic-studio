from typing import ClassVar, Optional, override

from PySide6.QtCore import QEvent, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QEnterEvent, QFont, QIcon, QPainter, QPaintEvent
from PySide6.QtWidgets import QApplication, QPushButton, QWidget


class IconButton(QPushButton):
    activated = Signal(tuple)

    def __init__(
        self,
        size: tuple[int, int],
        checkable: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.setCheckable(checkable)
        self.setFixedSize(*size)
        self.clicked.connect(self.handle_shift)
        self.icon_size = size

    def set_icon(self, icon_path: str) -> None:
        width, height = self.icon_size
        self.icon_path = icon_path
        icon = QIcon(icon_path)
        available_sizes = icon.availableSizes()
        if available_sizes and available_sizes[0].width() < width:
            pixmap = icon.pixmap(available_sizes[0])
            scaled_pixmap = pixmap.scaled(
                width,
                height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation,
            )
            icon = QIcon(scaled_pixmap)

        self.setIcon(icon)
        self.setIconSize(QSize(width, height))

    def set_tooltip(self, text: str) -> None:
        self.setToolTip(text)

    def handle_shift(self):
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.KeyboardModifier.ShiftModifier and self.isCheckable():
            self.setChecked(True)
            self.activated.emit(self)

        else:
            self.setChecked(False)


class SidebarButton(QPushButton):
    activated = Signal(tuple)

    def __init__(
        self,
        size: tuple[int, int],
        parent: Optional[QWidget] = None,
        checkable: bool = True,
    ):
        super().__init__(parent)
        self.setCheckable(checkable)
        self.setFixedSize(*size)
        self.clicked.connect(lambda: self.activated.emit(self))

    def set_icon(self, icon_path: str, icon_size: tuple[int, int]) -> None:
        width, height = icon_size
        icon = QIcon(icon_path)
        self.setIcon(icon)
        self.setIconSize(QSize(width, height))

    def set_tooltip(self, text: str) -> None:
        self.setToolTip(text)


class ConnectionButton(QPushButton):
    """Shows the connection status of every DCC as a stacked, labeled pill."""

    # Connection fires its callbacks on whichever thread noticed the state
    # change (the connect thread, the ping thread), and a widget may only be
    # touched on the GUI thread. Emit this instead of calling set_status
    # directly: the queued connection hops the change back onto the GUI thread.
    status_changed = Signal(str, bool)

    # key -> (pill label, tooltip name)
    DCCS: ClassVar[dict[str, tuple[str, str]]] = {
        "c4d": ("C4D", "Cinema 4D"),
        "nuke": ("NK", "Nuke"),
    }

    COLOR_ON = QColor("#2cd376")
    COLOR_ON_HOVER = QColor("#156337")
    COLOR_OFF = QColor("#c53a3e")
    COLOR_OFF_HOVER = QColor("#722224")

    PILL_HEIGHT = 18
    PILL_SPACING = 3

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._status = dict.fromkeys(self.DCCS, False)
        self._hovered = False

        count = len(self.DCCS)
        self.setFixedWidth(30)
        self.setFixedHeight(count * self.PILL_HEIGHT + (count - 1) * self.PILL_SPACING)

        self.status_changed.connect(self.set_status, Qt.ConnectionType.QueuedConnection)
        self._update_tooltip()

    def set_status(self, dcc: str, connected: bool):
        self._status[dcc] = connected
        self._update_tooltip()
        self.update()

    def is_connected(self, dcc: str) -> bool:
        return self._status[dcc]

    def _update_tooltip(self):
        lines = [
            f"{name}: {'connected' if self._status[k] else 'not connected'}"
            for k, (_, name) in self.DCCS.items()
        ]
        lines.append("Click to reconnect")
        self.setToolTip("\n".join(lines))

    @override
    def enterEvent(self, event: QEnterEvent):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    @override
    def leaveEvent(self, event: QEvent):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    @override
    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        font = QFont(self.font())
        font.setPointSize(7)
        font.setBold(True)
        painter.setFont(font)

        for i, (key, (label, _)) in enumerate(self.DCCS.items()):
            if self._status[key]:
                color = self.COLOR_ON_HOVER if self._hovered else self.COLOR_ON
            else:
                color = self.COLOR_OFF_HOVER if self._hovered else self.COLOR_OFF

            rect = QRectF(
                0,
                i * (self.PILL_HEIGHT + self.PILL_SPACING),
                self.width(),
                self.PILL_HEIGHT,
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            painter.drawRoundedRect(rect, 5, 5)

            painter.setPen(Qt.GlobalColor.white)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)
