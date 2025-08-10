from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from apic_studio.core import Asset
from apic_studio.services.tags import TagService
from apic_studio.ui.dialogs import TagDialog

from .buttons import IconButton
from .flow_layout import FlowLayout


class Tag(QWidget):
    remove = Signal(str)

    def __init__(self, label: str, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.text = label

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

    def init_widgets(self):
        self.label = QLabel(self.text)
        self.delete_btn = QPushButton("X")
        self.delete_btn.setFixedWidth(20)

    def init_layouts(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.delete_btn)

    def init_signals(self):
        self.delete_btn.clicked.connect(lambda: self.remove.emit(self.text))


class TagCollection(QWidget):
    tags_changed = Signal(list)

    def __init__(self, label: str, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.tag_svc = TagService()
        self.text = label
        self.tags: dict[str, Tag] = {}

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

    def init_widgets(self):
        self.label = QLabel(self.text)
        self.add_btn = QPushButton("Add Tag")

    def init_layouts(self):
        self.main_layout = FlowLayout(self)
        self.main_layout.addWidget(self.add_btn)

    def init_signals(self):
        self.add_btn.clicked.connect(self.add_tag_dialog)

    def add_tag_dialog(self):
        dialog = TagDialog(self.tag_svc.get_all())
        dialog.tags_selected.connect(self.on_tags_selected)
        dialog.tag_created.connect(self.on_tag_created)
        dialog.exec()

    def on_tag_created(self, tag: str):
        self.tag_svc.create(tag)

    def on_tags_selected(self, tags: list[str]):
        for t in tags:
            self.add_tag(t)

        self.tags_changed.emit(tags)

    def on_tag_delete(self, tag: str):
        widget = self.tags.pop(tag)
        widget.setParent(None)
        widget.deleteLater()

        self.tags_changed.emit(list(self.tags))

    def add_tag(self, tag: str):
        t = Tag(tag)
        t.remove.connect(self.on_tag_delete)
        self.main_layout.addWidget(t)
        self.tags[tag] = t

    def clear(self):
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if not item:
                continue
            widget = item.widget()
            widget.setParent(None)
            if widget is not self.add_btn:
                item.widget().deleteLater()
        self.tags.clear()
        self.main_layout.addWidget(self.add_btn)


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
        self.tag_collection = TagCollection("")
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
        self.form_layout.addRow("Tags", self.tag_collection)
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
        self.tag_collection.tags_changed.connect(self.on_tags_changed)

    def on_tags_changed(self, tags: list[str]):
        self.current_asset.metadata.tags = tags
        self.current_asset.metadata.save()
        print(tags)

        self.create_tags(tags)

    def create_tags(self, tags: list[str]):
        self.tag_collection.clear()
        for t in tags:
            self.tag_collection.add_tag(t)

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
        self.create_tags(asset.metadata.tags)
