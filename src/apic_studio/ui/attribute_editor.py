from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QKeySequence, QShortcut
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

    def __init__(self, label: str, parent: QWidget | None = None):
        super().__init__(parent)

        self.text = label

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

    def init_widgets(self):
        self.label = QLabel(self.text)
        self.delete_btn = QPushButton("×")
        self.delete_btn.setFixedWidth(20)
        self.delete_btn.setToolTip(f"Remove tag {self.text}")

    def init_layouts(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.delete_btn)

    def init_signals(self):
        self.delete_btn.clicked.connect(lambda: self.remove.emit(self.text))


class TagCollection(QWidget):
    tags_changed = Signal(list)
    tag_removed = Signal(str)

    def __init__(self, label: str, parent: QWidget | None = None):
        super().__init__(parent)

        self.tag_svc = TagService()
        self.text = label
        self.tags: dict[str, Tag] = {}

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

    def init_widgets(self):
        self.label = QLabel(self.text)
        self.add_btn = QPushButton("Edit Tags")

    def init_layouts(self):
        self.main_layout = FlowLayout(self)
        self.main_layout.addWidget(self.add_btn)

    def init_signals(self):
        self.add_btn.clicked.connect(self.add_tag_dialog)

    def add_tag_dialog(self):
        dialog = TagDialog(self.tag_svc.get_all(), list(self.tags), self.window())
        dialog.tags_selected.connect(self.on_tags_selected)
        dialog.tag_created.connect(self.on_tag_created)
        dialog.exec()

    def on_tag_created(self, tag: str):
        self.tag_svc.create(tag)

    def on_tags_selected(self, tags: list[str]):
        # the dialog hands back the full set, the editor rebuilds the widgets
        self.tags_changed.emit(tags)

    def on_tag_delete(self, tag: str):
        widget = self.tags.pop(tag)
        widget.setParent(None)
        widget.deleteLater()

        self.tag_removed.emit(tag)

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

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.current_asset = Asset(Path(), QImage(), Path())
        self._has_asset = False
        # notes edited but not saved yet
        self._dirty = False

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

        self.asset_name = QLineEdit()
        self.asset_name.setPlaceholderText("Select an asset")
        self.asset_name.setReadOnly(True)
        self.asset_ext = QLineEdit()
        self.asset_ext.setReadOnly(True)
        self.asset_size = QLineEdit()
        self.asset_size.setReadOnly(True)
        self.asset_path = QLineEdit()
        self.asset_path.setReadOnly(True)
        # not stored per asset (yet), so it's display only
        self.asset_renderer = QLineEdit("Redshift")
        self.asset_renderer.setReadOnly(True)
        self.tag_collection = TagCollection("")
        self.asset_notes = QTextEdit()
        self.asset_notes.setPlaceholderText("Notes about this asset")
        self.asset_notes.setStyleSheet(" border: 1px solid #222;")

        self.save_btn = QPushButton("Save")
        self.save_btn.setToolTip("Save notes (Ctrl+S)")
        self.save_shortcut = QShortcut(
            QKeySequence(QKeySequence.StandardKey.Save),
            self,
            context=Qt.ShortcutContext.WidgetWithChildrenShortcut,
        )

        self.set_editable(False)

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
        self.save_shortcut.activated.connect(self.on_save)
        self.asset_notes.textChanged.connect(self.on_notes_changed)
        self.load.connect(self.on_load)
        self.tag_collection.tags_changed.connect(self.on_tags_changed)
        self.tag_collection.tag_removed.connect(self.on_tag_removed)

    def on_tag_removed(self, tag: str):
        self.current_asset.metadata.tags.remove(tag)
        self.current_asset.metadata.save()

    def set_editable(self, editable: bool):
        """Notes and tags only make sense once an asset is selected."""
        self.asset_notes.setEnabled(editable)
        self.tag_collection.add_btn.setEnabled(editable)
        self.save_btn.setEnabled(editable and self._dirty)

    def on_notes_changed(self):
        self._dirty = True
        self.save_btn.setEnabled(self._has_asset)

    def flush(self):
        """Save notes that were edited but not saved yet."""
        if self._dirty:
            self.on_save()

    def on_tags_changed(self, tags: list[str]):
        # keep the order the tags were picked in, drop duplicates
        tag_list = list(dict.fromkeys(tags))
        self.current_asset.metadata.tags = tag_list
        self.current_asset.metadata.save()

        self.create_tags(tag_list)

    def create_tags(self, tags: list[str]):
        self.tag_collection.clear()
        for t in tags:
            self.tag_collection.add_tag(t)

    def on_save(self):
        if not self._has_asset:
            return

        self.current_asset.metadata.notes = self.asset_notes.toPlainText()
        self.current_asset.metadata.save()
        self._dirty = False
        self.save_btn.setEnabled(False)
        self.save.emit(self.current_asset)

    def on_load(self, asset: Asset):
        # switching assets would throw away unsaved notes
        self.flush()

        self.current_asset = asset
        self._has_asset = True
        asset.metadata.load()

        self.icon.set_icon(str(asset.icon_path))
        self.asset_name.setText(asset.name)
        self.asset_ext.setText(asset.suffix)
        self.asset_size.setText(asset.format_size())
        self.asset_path.setText(str(asset.path))
        self.asset_notes.blockSignals(True)
        self.asset_notes.setPlainText(asset.metadata.notes)
        self.asset_notes.blockSignals(False)
        self._dirty = False
        self.set_editable(True)
        self.create_tags(asset.metadata.tags)
