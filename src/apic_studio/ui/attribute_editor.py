from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from apic_studio.core import Asset

from .buttons import IconButton


class AttributeEditor(QWidget):
    save = Signal(Asset)
    load = Signal(Asset)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.current_asset = Asset(Path(), QIcon(), Path())

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

    def init_widgets(self):
        self.scroll_widget = QWidget()
        self.scroll_area = QScrollArea()
        self.scroll_area.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.scroll_area.setWidgetResizable(True)
        # self.scroll_area.setVerticalScrollBarPolicy(
        #    Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        # )
        self.setStyleSheet("background-color: #333;")
        self.scroll_area.setWidget(self.scroll_widget)

        self.banner = QWidget()

        icon_size = (350, 350)
        self.icon = IconButton(icon_size)
        self.icon.set_icon(":icons/tabler-icon-photo.png")

        self.asset_name = QLineEdit("Asset Name")
        self.asset_name.setReadOnly(True)
        self.asset_ext = QLineEdit("")
        self.asset_ext.setReadOnly(True)
        self.asset_size = QLineEdit("0MB")
        self.asset_size.setReadOnly(True)
        self.asset_path = QLineEdit("/path/to/asset")
        self.asset_path.setReadOnly(True)
        self.asset_renderer = QLineEdit("Redshift")
        self.asset_notes = QTextEdit("notes about asset...")
        self.asset_notes.setStyleSheet(" border: 1px solid #222;")

        self.save_btn = QPushButton("Save")

    def init_layouts(self):
        self.another_layout = QVBoxLayout()
        self.banner_layout = QVBoxLayout()
        self.main_layout = QVBoxLayout()
        self.form_layout = QFormLayout()

        self.form_layout.addRow("Name", self.asset_name)
        self.form_layout.addRow("Extension", self.asset_ext)
        self.form_layout.addRow("Size", self.asset_size)
        self.form_layout.addRow("Path", self.asset_path)
        self.form_layout.addRow("Renderer", self.asset_renderer)
        self.form_layout.addRow("Notes", self.asset_notes)
        self.form_layout.setContentsMargins(0, 0, 0, 0)

        self.button_layout = QHBoxLayout()
        self.button_layout.addStretch()
        self.button_layout.addWidget(self.save_btn)
        self.button_layout.setContentsMargins(0, 0, 0, 0)

        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        self.main_layout.addLayout(self.banner_layout)
        self.main_layout.addWidget(self.icon, alignment=Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addLayout(self.button_layout)

        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.addLayout(self.banner_layout)
        self.scroll_layout.addLayout(self.main_layout)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)

        self.another_layout.addWidget(self.scroll_area)
        self.another_layout.setContentsMargins(0, 0, 0, 0)

        self.setLayout(self.another_layout)

    def init_signals(self):
        self.save_btn.clicked.connect(self.on_save)
        self.load.connect(self.on_load)

    def on_save(self):
        self.current_asset.metadata.notes = self.asset_notes.toPlainText()
        self.current_asset.metadata.save()
        self.save.emit(self.current_asset)

    def on_load(self, asset: Asset):
        self.current_asset = asset
        self.icon.set_icon(str(asset.icon_path))
        self.asset_name.setText(asset.name)
        self.asset_ext.setText(asset.suffix)
        self.asset_size.setText(asset.format_size())
        self.asset_path.setText(str(asset.path))
        self.asset_notes.setText(asset.metadata.notes)
        asset.metadata.load()
