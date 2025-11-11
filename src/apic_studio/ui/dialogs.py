from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Literal, NamedTuple, Optional

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QCursor, QIcon, QMouseEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressDialog,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from apic_studio.core.settings import SettingsManager
from apic_studio.services import Backup, BackupManager
from shared.logger import Logger

from .buttons import IconButton


class CreatePoolDialog(QDialog):
    pool_created = Signal(tuple)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Create new Pool")
        self.setWindowIcon(QIcon(":icons/apic_logo.png"))
        self.setStyleSheet("QWidget {background-color: #333; color: #fff}")

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

    def init_widgets(self):
        self.name_edit = QLineEdit()

        self.folder_edit = QLineEdit()

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
        self.folder_layout.setContentsMargins(0, 0, 0, 0)
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
        self.setWindowIcon(QIcon(":icons/apic_logo.png"))
        self.setStyleSheet("QWidget {background-color: #333; color: #fff}")

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

    @dataclass(slots=True)
    class Data:
        name: str
        ext: str
        export_type: Literal["Save current Scene", "Export selected"]
        copy_textures: bool
        globalize_textures: bool

    finished = Signal(Data)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.setWindowTitle("Export")
        self.setWindowIcon(QIcon(":icons/apic_logo.png"))
        self.setStyleSheet("QWidget {background-color: #333; color: #fff}")

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

    def init_widgets(self):
        self.name_edit = QLineEdit("")
        self.name_edit.setFixedHeight(30)

        self.export_options = QComboBox()
        self.export_options.addItems([self.ExportType.EXPORT, self.ExportType.SAVE])

        self.copy_textues_check = QCheckBox()
        self.copy_textues_check.setChecked(True)
        self.globalize_textures = QCheckBox()
        self.globalize_textures.setChecked(True)

        buttons = (
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box = QDialogButtonBox(buttons)

    def init_layouts(self):
        self.main_layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()

        self.form_layout.addRow("Name", self.name_edit)
        self.form_layout.addRow("Export Options", self.export_options)
        self.form_layout.addRow("Globalize Textures", self.globalize_textures)
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

        data = self.Data(
            name,
            ext,
            self.ExportType(opt).value,
            self.copy_textues_check.isChecked(),
            self.globalize_textures.isChecked(),
        )

        self.finished.emit(data)


class ExportMaterialDialog(QDialog):
    @dataclass(slots=True)
    class Data:
        ext: str
        copy_textures: bool
        materials: list[str]
        globalize_textures: bool

    finished = Signal(Data)

    def __init__(self, materials: list[str], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.materials = materials
        self._widgets: list[tuple[QCheckBox, QLabel]] = []

        self.setWindowTitle("Export")
        self.setWindowIcon(QIcon(":icons/apic_logo.png"))
        self.setStyleSheet("QWidget {background-color: #333; color: #fff}")

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

    def init_widgets(self):
        self.copy_textues_check = QCheckBox("Copy Textures and Repath")
        self.copy_textues_check.setChecked(True)
        self.globalize_textures = QCheckBox("Globalize Textures")
        self.globalize_textures.setChecked(True)

        self.select_all = QPushButton("Select All")
        self.deselect_all = QPushButton("Deselect All")

        self.scroll_widget = QWidget()
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.scroll_area.setWidgetResizable(True)

        buttons = (
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box = QDialogButtonBox(buttons)

    def init_layouts(self):
        self.main_layout = QVBoxLayout(self)
        self.select_layout = QHBoxLayout()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)

        for mtl in self.materials:
            layout = self.add_material_row(mtl)
            self.scroll_layout.addLayout(layout)
        self.scroll_layout.addStretch()

        self.select_layout.addStretch()
        self.select_layout.addWidget(self.select_all)
        self.select_layout.addWidget(self.deselect_all)

        self.main_layout.addWidget(self.scroll_area)
        self.main_layout.addWidget(
            self.copy_textues_check, alignment=Qt.AlignmentFlag.AlignRight
        )
        self.main_layout.addWidget(
            self.globalize_textures, alignment=Qt.AlignmentFlag.AlignRight
        )
        self.main_layout.addLayout(self.select_layout)
        self.main_layout.addWidget(self.button_box)

    def init_signals(self):
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.select_all.clicked.connect(self.select_all_materials)
        self.deselect_all.clicked.connect(self.deselect_all_materials)

    def add_material_row(self, name: str):
        layout = QHBoxLayout()
        checkbox = QCheckBox("")
        label = QLabel(name)

        layout.setSpacing(10)
        layout.addWidget(checkbox)
        layout.addWidget(label, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()

        self._widgets.append((checkbox, label))
        return layout

    def get_selected_materials(self) -> list[str]:
        return [label.text() for check, label in self._widgets if check.isChecked()]

    def select_all_materials(self):
        for check, _ in self._widgets:
            check.setChecked(True)

    def deselect_all_materials(self):
        for check, _ in self._widgets:
            check.setChecked(False)

    def accept(self) -> None:
        super().accept()
        data = self.Data(
            "c4d",
            self.copy_textues_check.isChecked(),
            self.get_selected_materials(),
            self.globalize_textures.isChecked(),
        )
        self.finished.emit(data)


class ScreenshotResult(NamedTuple):
    geometry: tuple[int, int, int, int]
    folder: Path
    asset_name: str


class ScreenshotDialog(QDialog):
    accepted = Signal(ScreenshotResult)

    def __init__(self, model_path: Path, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet("border: 2px solid black;")
        self.setWindowOpacity(0.7)
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
        self.accepted.emit(
            ScreenshotResult(
                (
                    self.x(),
                    self.y(),
                    self.width(),
                    self.height(),
                ),
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


class SettingsDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setWindowIcon(QIcon(":icons/apic_logo.png"))
        self.setStyleSheet("QWidget {background-color: #333; color: #fff}")
        self.settings = SettingsManager()

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

        self.load()

    def init_widgets(self):
        self.label = QLabel("Settings")
        self.label.setContentsMargins(10, 0, 0, 0)

        self.core_settings = QGroupBox("Core Settings")
        self.socket_port = QSpinBox()
        self.socket_port.setRange(0, 2**16)
        self.socket_port.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.addr = QLineEdit("localhost")
        self.root_path = QLineEdit(self.settings.CoreSettings.root_path)
        self.browse_root = QPushButton(QIcon(":icons/tabler-icon-folder-open.png"), "")

        self.window_settings = QGroupBox("Window Settings")

        self.material_settings = QGroupBox("Material Settings")
        self.render_scene = QLineEdit("Path/To/Render/Scene")
        self.browse_render_scene = QPushButton(
            QIcon(":icons/tabler-icon-folder-open.png"), ""
        )
        self.render_object = QLineEdit("Name of shaderball Object")
        self.render_cam = QLineEdit("Render Camera")
        self.render_resolution_x = QSpinBox()
        self.render_resolution_x.setRange(0, 5000)
        self.render_resolution_x.setButtonSymbols(
            QAbstractSpinBox.ButtonSymbols.NoButtons
        )
        self.render_resolution_y = QSpinBox()
        self.render_resolution_y.setRange(0, 5000)
        self.render_resolution_y.setButtonSymbols(
            QAbstractSpinBox.ButtonSymbols.NoButtons
        )

        self.model_settings = QGroupBox("Model Settings")
        self.screenshot_opacity = QDoubleSpinBox()
        self.screenshot_opacity.setRange(0, 1)
        self.screenshot_opacity.setButtonSymbols(
            QAbstractSpinBox.ButtonSymbols.NoButtons
        )

        self.hdri_settings = QGroupBox("HDRI Settings")

        self.save = QPushButton("Save")
        self.ok_btn = QPushButton("OK")

    def init_layouts(self):
        self.settings_groups_layout = QVBoxLayout(self)

        self.root_layout = QHBoxLayout()
        self.root_layout.addWidget(self.root_path)
        self.root_layout.addWidget(self.browse_root)

        self.core_settings_layout = QFormLayout(self.core_settings)
        self.core_settings_layout.addRow("Cinema 4D socket address", self.addr)
        self.core_settings_layout.addRow("Cinema 4D socket port", self.socket_port)
        self.core_settings_layout.addRow("Root Path", self.root_layout)

        self.general_settings_layout = QFormLayout(self.window_settings)

        self.render_scene_layout = QHBoxLayout()
        self.render_scene_layout.addWidget(self.render_scene)
        self.render_scene_layout.addWidget(self.browse_render_scene)

        self.resolution_layout = QHBoxLayout()
        self.resolution_layout.addWidget(self.render_resolution_x)
        self.resolution_layout.addWidget(self.render_resolution_y)

        self.material_settings_layout = QFormLayout(self.material_settings)
        self.material_settings_layout.addRow(
            QLabel("Render Scene"), self.render_scene_layout
        )
        self.material_settings_layout.addRow(
            QLabel("Render Object"), self.render_object
        )
        self.material_settings_layout.addRow(QLabel("Render Camera"), self.render_cam)
        self.material_settings_layout.addRow(
            QLabel("Render Resolution"), self.resolution_layout
        )

        self.model_settings_layout = QFormLayout(self.model_settings)
        self.model_settings_layout.addRow(
            QLabel("Screenshot Widget Opacity"), self.screenshot_opacity
        )

        self.hdri_settings_layout = QFormLayout(self.hdri_settings)

        self.save_layout = QHBoxLayout()
        self.save_layout.addStretch()
        self.save_layout.addWidget(self.save)
        self.save_layout.addWidget(self.ok_btn)

        self.settings_groups_layout.addWidget(self.core_settings)
        self.settings_groups_layout.addWidget(self.window_settings)
        self.settings_groups_layout.addWidget(self.material_settings)
        self.settings_groups_layout.addWidget(self.model_settings)
        self.settings_groups_layout.addWidget(self.hdri_settings)
        self.settings_groups_layout.addLayout(self.save_layout)
        self.settings_groups_layout.addStretch()

    def init_signals(self):
        self.browse_render_scene.clicked.connect(self.open_render_scene)
        self.browse_root.clicked.connect(self.set_root_dir)
        self.save.clicked.connect(self.store)

    def open_render_scene(self):
        file, _ = QFileDialog().getOpenFileName(
            self, "Browse Render Scene", filter="Cinema 4D Files (*.c4d)"
        )
        if not file:
            return

        self.render_scene.setText(file)

    def set_root_dir(self):
        dir = QFileDialog().getExistingDirectory(self, "Browse Folder")
        if not dir:
            return

        self.settings.CoreSettings.set_root_path(dir)
        self.root_path.setText(dir)

    def load(self):
        core = self.settings.CoreSettings
        mat = self.settings.MaterialSettings
        _ = self.settings.WindowSettings
        mod = self.settings.ModelSettings
        _ = self.settings.HdriSettings

        self.socket_port.setValue(core.socket_port)
        self.addr.setText(core.socket_addr)

        self.render_scene.setText(mat.render_scene)
        self.render_object.setText(mat.render_object)
        self.render_cam.setText(mat.render_cam)
        self.render_resolution_x.setValue(mat.render_res_x)
        self.render_resolution_y.setValue(mat.render_res_y)

        self.screenshot_opacity.setValue(mod.screenshot_opacity)

    def store(self):
        core = self.settings.CoreSettings
        mat = self.settings.MaterialSettings
        _ = self.settings.WindowSettings
        mod = self.settings.ModelSettings

        core.socket_port = self.socket_port.value()
        core.socket_addr = self.addr.text()

        mat.render_res_x = self.render_resolution_x.value()
        mat.render_res_y = self.render_resolution_y.value()
        mat.render_object = self.render_object.text()
        mat.render_scene = self.render_scene.text()
        mat.render_cam = self.render_cam.text()

        mod.screenshot_opacity = self.screenshot_opacity.value()


class BackupDialog(QDialog):
    imported = Signal(Path)
    opened = Signal(Path)
    referenced = Signal(Path)

    def __init__(
        self,
        archive_path: Path,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.archive_path = archive_path
        self.elements: dict[str, tuple[QTreeWidgetItem, Backup]] = {}
        self.backup = BackupManager()

        self.setWindowIcon(QIcon(":icons/apic_logo.png"))
        self.setWindowTitle("Backup Viewer")
        self.setStyleSheet("QWidget {background-color: #333; color: #fff}")

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

    def init_widgets(self):
        self.open_model = QPushButton("Open")
        self.import_model = QPushButton("Import")
        self.reference_model = QPushButton("Reference")

        self.tree_widget = QTreeWidget(self)
        self.tree_widget.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.tree_widget.setHeaderLabels(["Backups"])

        for pool_backup in self.backup.load_from_pool(self.archive_path):
            archive_item = QTreeWidgetItem(
                self.tree_widget, [pool_backup[0].original_name]
            )
            for asset_backup in pool_backup:
                item = QTreeWidgetItem(archive_item, [asset_backup.name])
                self.elements[asset_backup.name] = (item, asset_backup)

    def init_layouts(self):
        self.main_layout = QVBoxLayout(self)
        self.select_layout = QHBoxLayout()

        self.select_layout.addStretch()
        self.select_layout.addWidget(self.open_model)
        self.select_layout.addWidget(self.import_model)
        self.select_layout.addWidget(self.reference_model)

        self.main_layout.addWidget(self.tree_widget)
        self.main_layout.addLayout(self.select_layout)

    def init_signals(self):
        self.import_model.clicked.connect(lambda: self.import_selection())
        self.reference_model.clicked.connect(lambda: self.reference_selection())
        self.open_model.clicked.connect(lambda: self.open_selection())

    def import_selection(self):
        path = self.get_selected_path()
        if not path:
            Logger.error(f"can't import model, path is: {path}")
            return
        self.imported.emit(path)
        self.close()

    def reference_selection(self):
        path = self.get_selected_path()
        if not path:
            Logger.error(f"can't reference model, path is: {path}")
            return
        self.referenced.emit(path)
        self.close()

    def open_selection(self):
        path = self.get_selected_path()
        if not path:
            Logger.error(f"can't open model, path is: {path}")
            return
        self.opened.emit(path)
        self.close()

    def get_item_level(self, item: QTreeWidgetItem):
        level = 0
        while i := item.parent():
            item = i
            level += 1
        return level

    def get_selected_path(self) -> Optional[Path]:
        selected = self.tree_widget.selectedItems()[0]
        item_name = selected.text(0)

        _, backup = self.elements[item_name]

        if not self.get_item_level(selected) == 1:
            Logger.error("select an archived version instead of the group")
            return None

        return backup.path


class CreateBackupDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Create Backup")
        self.setWindowIcon(QIcon(":icons/apic_logo.png"))
        self.setStyleSheet("QWidget {background-color: #333; color: #fff}")

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

    def init_widgets(self):
        self.label = QLabel("Would you like to create a backup before opening?")

        buttons = (
            QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No
        )
        self.button_box = QDialogButtonBox(buttons)

    def init_layouts(self):
        self.main_layout = QVBoxLayout(self)
        self.buttons_layout = QHBoxLayout()

        self.main_layout.addWidget(self.label)
        self.main_layout.addWidget(self.button_box)

    def init_signals(self):
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)


class ImportModelsDialog(QDialog):
    finished = Signal(list)

    def __init__(self, models: dict[str, Path], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.models = models
        self._widgets: list[tuple[QCheckBox, QLabel]] = []

        self.setWindowTitle("Import Models")
        self.setWindowIcon(QIcon(":icons/apic_logo.png"))
        self.setStyleSheet("QWidget {background-color: #333; color: #fff}")

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

    def init_widgets(self):
        self.select_all_btn = QPushButton("Select All")
        self.deselect_all_btn = QPushButton("Deselect All")

        self.scroll_widget = QWidget()
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.scroll_widget)
        self.scroll_area.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.scroll_area.setWidgetResizable(True)

        buttons = (
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box = QDialogButtonBox(buttons)

    def init_layouts(self):
        self.main_layout = QVBoxLayout(self)
        self.select_layout = QHBoxLayout()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)

        for mtl in self.models:
            layout = self.add_row(mtl)
            self.scroll_layout.addLayout(layout)
        self.scroll_layout.addStretch()

        self.select_layout.addStretch()
        self.select_layout.addWidget(self.select_all_btn)
        self.select_layout.addWidget(self.deselect_all_btn)

        self.main_layout.addWidget(self.scroll_area)
        self.main_layout.addLayout(self.select_layout)
        self.main_layout.addWidget(self.button_box)

    def init_signals(self):
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.select_all_btn.clicked.connect(self.select_all)
        self.deselect_all_btn.clicked.connect(self.deselect_all)

    def add_row(self, name: str):
        layout = QHBoxLayout()
        checkbox = QCheckBox("")
        label = QLabel(name)

        layout.setSpacing(10)
        layout.addWidget(checkbox)
        layout.addWidget(label, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addStretch()

        self._widgets.append((checkbox, label))
        return layout

    def get_selected(self) -> list[Path]:
        return [
            self.models[label.text()]
            for check, label in self._widgets
            if check.isChecked()
        ]

    def select_all(self):
        for check, _ in self._widgets:
            check.setChecked(True)

    def deselect_all(self):
        for check, _ in self._widgets:
            check.setChecked(False)

    def accept(self) -> None:
        super().accept()
        self.finished.emit(self.get_selected())


class ProgressDialog(QProgressDialog):
    def __init__(
        self,
        labelText: str,
        minimum: int,
        maximum: int,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(
            labelText,
            "Cancel",
            minimum,
            maximum,
            parent,
        )
        self.setWindowModality(Qt.WindowModality.WindowModal)
        # self.setCancelButton(None)
        self.setWindowIcon(QIcon(":icons/apic_logo.png"))
        self.setStyleSheet("QWidget {background-color: #333; color: #fff}")
        self.setWindowTitle("Progress")


class TagDialog(QDialog):
    tags_selected = Signal(list)
    tag_created = Signal(str)

    def __init__(self, tags: list[str], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowIcon(QIcon(":icons/apic_logo.png"))
        self.setStyleSheet("QWidget {background-color: #333; color: #fff}")
        self.setWindowTitle("Add Tags")

        self.all_tags = tags
        self._button_cache: dict[str, QPushButton] = {}

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

        self.add_tags(self.all_tags)

    def init_widgets(self):
        self.name_edit = QLineEdit("")
        # self.name_edit.setFixedHeight(30)

        self.scroll_widget = QWidget()
        self.scroll_area = QScrollArea()
        self.scroll_area.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.scroll_area.setWidgetResizable(True)
        # self.scroll_area.setVerticalScrollBarPolicy(
        #     Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        # )
        self.scroll_area.setWidget(self.scroll_widget)

        buttons = (
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box = QDialogButtonBox(buttons)

    def init_layouts(self):
        self.tag_layout = QVBoxLayout()
        self.main_layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()

        self.form_layout.addRow(QLabel("Tag Name"), self.name_edit)

        self.scroll_widget.setLayout(self.tag_layout)

        self.main_layout.addWidget(self.scroll_area)
        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addWidget(self.button_box)

    def init_signals(self):
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def accept(self) -> None:
        tags: list[str] = []
        for tag, btn in self._button_cache.items():
            if not btn.isChecked():
                continue
            tags.append(tag)

        if (t := self.name_edit.text()) and t not in self._button_cache.keys():
            tag = self.name_edit.text()
            tags.append(tag)
            self.tag_created.emit(tag)

        self.tags_selected.emit(tags)
        super().accept()

    def add_tags(self, tags: list[str]):
        for tag in tags:
            btn = QPushButton(tag)
            btn.setCheckable(True)
            self._button_cache[tag] = btn
            self.tag_layout.addWidget(btn)

        self.tag_layout.addStretch()


class RenameAssetDialog(QDialog):
    asset_renamed = Signal(str)

    def __init__(self, old_name: str, parent: Optional[QWidget] = None):
        super().__init__(parent)

        self.old_name = old_name

        self.setWindowTitle("Rename Asset")
        self.setWindowIcon(QIcon(":icons/apic_logo.png"))
        self.setStyleSheet("QWidget {background-color: #333; color: #fff}")

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

    def init_widgets(self):
        self.name_edit = QLineEdit()
        self.old_name_edit = QLineEdit(self.old_name)
        self.old_name_edit.setReadOnly(True)

        buttons = (
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box = QDialogButtonBox(buttons)

    def init_layouts(self):
        self.main_layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()
        self.folder_layout = QHBoxLayout()
        self.folder_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.folder_layout.setContentsMargins(0, 0, 0, 0)
        self.buttons_layout = QHBoxLayout()

        self.form_layout.addRow(QLabel("Old Name"), self.old_name_edit)
        self.form_layout.addRow(QLabel("New Name"), self.name_edit)

        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addWidget(self.button_box)

    def init_signals(self):
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def accept(self) -> None:
        self.asset_renamed.emit(self.name_edit.text())
        super().accept()


def files_dialog(title: str = "Select Files") -> tuple[list[str], str]:
    folder = QFileDialog.getOpenFileNames(caption=title)
    return folder


def folder_dialog(title: str = "Select Folder") -> str:
    folder = QFileDialog.getExistingDirectory(caption=title)
    return folder
