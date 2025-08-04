import shutil
from pathlib import Path
from typing import Optional, override

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

STYLE = """
ViewportButton QPushButton{
    background-color: rgb(60,60,60);
    border: 1px solid black;
    border-bottom: none;
    border-bottom: none;
}
ViewportButton QLabel{
    font-size: 10pt;
    background-color: rgb(60,60,60);
    border: 1px solid black;
    border-top: none;
    border-bottom: 0.5px solid black;
}
ViewportButton QPushButton::hover{
    background-color: rgb(128,128,128);
}

ViewportButton QPushButton::checked{
    background-color: rgb(235, 177, 52);
}
"""


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


class ViewportButton(QWidget):
    clicked = Signal()

    def __init__(
        self,
        file: Path,
        button_size: tuple[int, int],
        checkable: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.button_size = button_size
        self.name = file.stem
        self.suffix = file.suffix
        self.checkable = checkable
        self.file = file

        self.setMinimumSize(*button_size)
        self.setToolTip(file.stem)
        self.setStyleSheet(STYLE)

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

    def init_widgets(self):
        self.icon = IconButton(self.button_size, self.checkable)
        self.label = QLabel(self.name)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setContentsMargins(0, 3, 0, 5)
        self.label.setMaximumWidth(self.button_size[0])

        self.file_size = QLabel("Size: ")
        self.file_size.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.file_size.setContentsMargins(0, 5, 0, 5)
        self.file_size.setStyleSheet(
            "border-right: none;border-bottom:1px solid black; font-size: 8pt;"
        )
        self.file_type = QLabel("Type: ")
        self.file_type.setStyleSheet(
            "border-left: none;border-bottom:1px solid black;font-size: 8pt;"
        )
        self.file_type.setContentsMargins(0, 5, 0, 5)
        self.file_type.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def init_layouts(self):
        self.main_layout = QVBoxLayout(self)
        self.info_layout = QHBoxLayout()

        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.info_layout.addWidget(self.file_size)
        self.info_layout.addWidget(self.file_type)

        self.main_layout.setSpacing(0)
        self.main_layout.addWidget(self.icon)
        self.main_layout.addWidget(self.label)
        self.main_layout.addLayout(self.info_layout)

    def init_signals(self):
        self.icon.clicked.connect(self.clicked.emit)

    @staticmethod
    def _format_filesize(size: int) -> str:
        # bytes
        filesize = f"{size / 1_000:.2f}KB"
        if size >= 100_000_000:
            filesize = f"{size / 1_000_000_000:.2f}GB"
        elif size >= 100_000:
            filesize = f"{size / 1_000_000:.2f}MB"

        return filesize

    def set_file(self, file: Path, size: int, filetype: str):
        filesize = self._format_filesize(size)
        self.file_size.setText(f"Size: {filesize}")
        self.file_type.setText(f"Type: {filetype}")
        self.file = file

    def set_thumbnail(self, icon: QIcon, size: int):
        self.icon.setIcon(icon)
        self.icon.setIconSize(QSize(size, size))

    @override
    def deleteLater(self):
        if self.file.is_dir():
            shutil.rmtree(self.file, ignore_errors=True)
        else:
            shutil.rmtree(self.file.parent, ignore_errors=True)
        super().deleteLater()


class ConnectionButton(QPushButton):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setFixedWidth(30)
        self.setFixedHeight(30)
        self.setIconSize(QSize(28, 28))

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
