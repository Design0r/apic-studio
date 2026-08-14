from typing import Optional

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
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
    # Connection fires its callbacks on whichever thread noticed the state
    # change (the connect thread, the ping thread), and a widget may only be
    # touched on the GUI thread. Emit these instead of calling the setters
    # directly: the queued connections hop the change back onto the GUI thread.
    connected = Signal()
    disconnected = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedWidth(30)
        self.setFixedHeight(30)
        self.setIconSize(QSize(28, 28))

        self.connected.connect(self.set_connected, Qt.ConnectionType.QueuedConnection)
        self.disconnected.connect(
            self.set_disconnected, Qt.ConnectionType.QueuedConnection
        )

        self.set_disconnected()

    def set_connected(self):
        self.setStyleSheet(
            "ConnectionButton{background-color: #2cd376;} ConnectionButton::hover{background-color: #156337}"
        )
        self.setIcon(QIcon(":icons/icon-power-on.png"))

    def set_disconnected(self):
        self.setStyleSheet(
            "ConnectionButton{background-color: #c53a3e;} ConnectionButton::hover{background-color: #722224}"
        )
        self.setIcon(QIcon(":icons/icon-power-off.png"))
