from enum import StrEnum
from pathlib import Path
from typing import Literal, NamedTuple, Optional, TypedDict

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QCursor, QMouseEvent
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from .buttons import IconButton


class CreatePoolDialog(QDialog):
    pool_created = Signal(tuple)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Create new Pool")

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

    def init_widgets(self):
        self.name_edit = QLineEdit("")
        self.name_edit.setFixedHeight(30)

        self.folder_edit = QLineEdit("")
        self.folder_edit.setFixedHeight(30)

        self.open_file_dialog = IconButton((27, 27))
        self.open_file_dialog.set_icon(":icons/tabler-icon-folder-open.png")
        self.open_file_dialog.set_tooltip("Open Folder")

        buttons = (
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box = QDialogButtonBox(buttons)

    def init_layouts(self):
        self.main_layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()
        self.folder_layout = QHBoxLayout()
        self.folder_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.buttons_layout = QHBoxLayout()

        self.folder_layout.addWidget(self.folder_edit)
        self.folder_layout.addWidget(self.open_file_dialog)

        self.form_layout.addRow(QLabel("Pool Name"), self.name_edit)
        self.form_layout.addRow(QLabel("Pool Path"), self.folder_layout)

        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addWidget(self.button_box)

    def init_signals(self):
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.open_file_dialog.clicked.connect(self.browse_folder)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Pool Folder")
        if not folder:
            return
        self.folder_edit.setText(folder)

    def accept(self) -> None:
        data = (self.name_edit.text(), Path(self.folder_edit.text()))
        self.pool_created.emit(data)
        super().accept()


class DeletePoolDialog(QDialog):
    pool_deleted = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.setWindowTitle("Delete current Pool")

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

    def init_widgets(self):
        self.label = QLabel("do you want to delete the current pool?")

        buttons = (
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box = QDialogButtonBox(buttons)

    def init_layouts(self):
        self.main_layout = QVBoxLayout(self)
        self.buttons_layout = QHBoxLayout()

        self.buttons_layout.addStretch()
        self.buttons_layout.addWidget(self.button_box)

        self.main_layout.addWidget(self.label)
        self.main_layout.addLayout(self.buttons_layout)

    def init_signals(self):
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def accept(self) -> None:
        self.pool_deleted.emit()
        super().accept()


class ExportModelDialog(QDialog):
    class ExportType(StrEnum):
        SAVE = "Save current Scene"
        EXPORT = "Export selected"

    class Data(TypedDict):
        name: str
        ext: str
        export_type: Literal["Save current Scene", "Export selected"]
        copy_textures: bool

    finished = Signal(Data)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.setWindowTitle("Export")

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

    def init_widgets(self):
        self.name_edit = QLineEdit("")
        self.name_edit.setFixedHeight(30)

        self.export_options = QComboBox()
        self.export_options.addItems([self.ExportType.EXPORT, self.ExportType.SAVE])

        self.copy_textues_check = QCheckBox("")

        buttons = (
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box = QDialogButtonBox(buttons)

    def init_layouts(self):
        self.main_layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()

        self.form_layout.addRow("Name", self.name_edit)
        self.form_layout.addRow("Export Options", self.export_options)
        self.form_layout.addRow("Copy Textures and Repath", self.copy_textues_check)

        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addWidget(self.button_box)

    def init_signals(self):
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def accept(self) -> None:
        super().accept()
        opt = self.export_options.currentText()
        name, ext = (self.name_edit.text(), "c4d")

        data = {
            "name": name,
            "ext": ext,
            "export_type": self.ExportType(opt).value,
            "copy_textures": self.copy_textues_check.isChecked(),
        }

        self.finished.emit(data)


class ScreenshotResult(NamedTuple):
    geometry: tuple[int, int, int, int]
    folder: Path
    asset_name: str


class ScreenshotDialog(QDialog):
    take_screenshot = Signal(ScreenshotResult)

    def __init__(self, model_path: Path, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet("border: 2px solid black;")
        self.setWindowOpacity(0.3)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)

        self.resize(300, 300)

        self.model_path = model_path

        self._dragPos = QPoint()

        self._resize = False

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

    def init_widgets(self):
        buttons = (
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_group = QDialogButtonBox(buttons)

    def init_layouts(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.main_layout.addStretch()
        self.main_layout.addWidget(self.button_group)

    def init_signals(self):
        self.button_group.accepted.connect(self.accept)
        self.button_group.rejected.connect(self.reject)

    def accept(self):
        self.take_screenshot.emit(
            ScreenshotResult(
                (self.x(), self.y(), self.width(), self.height()),
                self.model_path.parent,
                self.model_path.stem,
            )
        )

        super().accept()

    def mousePressEvent(self, event: QMouseEvent):
        # Enable resizing if the mouse is at the border of the window
        if (abs(event.x() - self.width()) < 10) or (
            abs(event.y() - self.height()) < 10
        ):
            self._resize = True
        else:
            self._dragPos = event.globalPos()

    def mouseMoveEvent(self, event: QMouseEvent):
        if (abs(event.x() - self.width()) < 10) or (
            abs(event.y() - self.height()) < 10
        ):
            self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))

        else:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

        if event.buttons() == Qt.MouseButton.LeftButton:
            if self._resize:
                self.resize(event.x(), event.x())

            else:
                diff = event.globalPos() - self._dragPos
                new_pos = self.pos() + diff
                self.move(new_pos)
                self._dragPos = event.globalPos()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._resize = False
        self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
