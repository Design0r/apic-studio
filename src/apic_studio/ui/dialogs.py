from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
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
