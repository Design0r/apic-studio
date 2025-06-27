from enum import Enum
from pathlib import Path
from typing import Callable, Optional, Union, override

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from apic_studio.services.pools import PoolManager
from apic_studio.ui.dialogs import CreatePoolDialog, DeletePoolDialog, ExportModelDialog
from apic_studio.ui.lines import VLine
from shared.logger import Logger

from .buttons import IconButton, SidebarButton

SIDEBAR_STYLE = """
QWidget{
    background-color: rgb(38,38,38);
    color: rgb(255,255,255);
}

QPushButton{
    background-color: none;
    border-radius: 5px;
}

QPushButton::hover{
    background-color: rgb(235, 177, 52);
}

QPushButton::checked{
    background-color: rgb(235, 177, 52);
}
"""

TOOLBAR_STYLE = """
QWidget{
    background-color: rgb(50,50,50);
}

"""

STATUSBAR_STYLE = """
QWidget{
    background-color: rgb(50,50,50);
}


QLabel{
    font-size: 8pt;
    color: white;
}
"""


class ToolbarDirection(Enum):
    Horizontal = 0
    Vertical = 1


class Toolbar(QWidget):
    def __init__(
        self,
        direction: ToolbarDirection,
        thickness: int,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.direction = direction
        self.thickness = thickness

        self.setStyleSheet(TOOLBAR_STYLE)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

    def init_widgets(self):
        if self.direction == ToolbarDirection.Horizontal:
            self.setFixedHeight(self.thickness)
        elif self.direction == ToolbarDirection.Vertical:
            self.setFixedWidth(self.thickness)

    def init_layouts(self) -> None:
        if self.direction == ToolbarDirection.Horizontal:
            self.main_layout = QHBoxLayout(self)
            self.main_layout.setContentsMargins(2, 2, 2, 2)
            return

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(2, 2, 2, 2)

    def init_signals(self):
        pass

    def add_widgets(self, widgets: list[QWidget], stretch: bool = True):
        for widget in widgets:
            self.main_layout.addWidget(widget)

        if stretch:
            self.main_layout.addStretch()

    def add_widget(self, widget: QWidget):
        self.main_layout.addWidget(widget)


class Sidebar(Toolbar):
    def __init__(self, width: int, parent: Optional[QWidget] = None):
        super().__init__(ToolbarDirection.Vertical, width, parent)
        self.setStyleSheet(SIDEBAR_STYLE)
        self.buttons = (
            self.materials,
            self.models,
            self.lightsets,
            self.hdris,
            self.utilities,
            self.help,
            self.about,
            self.settings_btn,
        )

    @override
    def init_widgets(self):
        super().init_widgets()

        size = 30
        btn_size = (size, size)
        icon_size = btn_size

        self.materials = SidebarButton(btn_size)
        self.materials.set_icon(":icons/tabler-icon-crystal-ball.png", icon_size)
        self.materials.set_tooltip("Materials")
        self.materials.activated.connect(self.highlight_modes)

        self.models = SidebarButton(btn_size)
        self.models.set_icon(":icons/tabler-icon-box.png", icon_size)
        self.models.set_tooltip("Models")
        self.models.activated.connect(self.highlight_modes)

        self.lightsets = SidebarButton(btn_size)
        self.lightsets.set_icon(":icons/tabler-icon-lamp.png", icon_size)
        self.lightsets.set_tooltip("Lightsets")
        self.lightsets.activated.connect(self.highlight_modes)

        self.hdris = SidebarButton(btn_size)
        self.hdris.set_icon(":icons/tabler-icon-bulb.png", icon_size)
        self.hdris.set_tooltip("HDRIs")
        self.hdris.activated.connect(self.highlight_modes)

        self.utilities = SidebarButton(btn_size)
        self.utilities.set_icon(":icons/tabler-icon-script.png", icon_size)
        self.utilities.set_tooltip("Utilities")
        self.utilities.activated.connect(self.highlight_modes)

        self.help = SidebarButton(btn_size)
        self.help.set_icon(":icons/tabler-icon-help.png", icon_size)
        self.help.set_tooltip("Help")
        self.help.activated.connect(self.highlight_modes)

        self.about = SidebarButton(btn_size)
        self.about.set_icon(":icons/tabler-icon-info-circle.png", icon_size)
        self.about.set_tooltip("About Render Vault")
        self.about.activated.connect(self.highlight_modes)

        self.settings_btn = SidebarButton(btn_size)
        self.settings_btn.set_icon(":icons/tabler-icon-settings.png", icon_size)
        self.settings_btn.set_tooltip("Settings")
        self.settings_btn.activated.connect(self.highlight_modes)

        self.conn_btn = QPushButton("D")

    def _add_button(
        self,
        size: tuple[int, int],
        icon: str,
        icon_size: tuple[int, int],
        tooltip: str,
        activated_fn: Callable[..., None],
    ):
        pass

    @override
    def init_layouts(self) -> None:
        super().init_layouts()
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.main_layout.addWidget(self.materials)
        self.main_layout.addWidget(self.models)
        self.main_layout.addWidget(self.lightsets)
        self.main_layout.addWidget(self.hdris)
        self.main_layout.addWidget(self.utilities)
        self.main_layout.addStretch()
        self.main_layout.addWidget(self.help)
        self.main_layout.addWidget(self.about)
        self.main_layout.addWidget(self.settings_btn)
        self.main_layout.addWidget(self.conn_btn)

    def highlight_modes(self, button: Union[SidebarButton, int]):
        for btn in self.buttons:
            btn.setChecked(False)

        if isinstance(button, SidebarButton):
            button.setChecked(True)
        else:
            self.buttons[button - 1].setChecked(True)


class Status:
    LoadingUI = "Loading UI"
    LoadingAssets = "Loading Assets"
    Idle = "Idle"


class Statusbar(Toolbar):
    def __init__(
        self,
        thickness: int,
        direction: ToolbarDirection = ToolbarDirection.Horizontal,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(direction, thickness, parent)
        self.thickness = thickness
        self.setStyleSheet(STATUSBAR_STYLE)

    @override
    def init_widgets(self):
        super().init_widgets()
        self.info = QLineEdit("")
        self.info.setReadOnly(True)
        self.info.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.info.setCursorPosition(0)
        self.info.setMinimumWidth(20)

        self.clear_btn = QPushButton("x")
        self.clear_btn.setFixedWidth(15)
        self.clear_btn.setStyleSheet(
            "QPushButton{border: none;}QPushButton::hover{background-color: rgb(100,100,100);}"
        )

    @override
    def init_layouts(self) -> None:
        super().init_layouts()
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.main_layout.setContentsMargins(0, 0, 10, 0)

        self.main_layout.addWidget(self.info)
        self.main_layout.addWidget(self.clear_btn)

    @override
    def init_signals(self) -> None:
        super().init_signals()
        Logger.register_callback(self.update_info)
        self.clear_btn.clicked.connect(lambda: self.update_info("Clear", ""))

    def update_info(self, level: str, text: str) -> None:
        self.info.setText(text)

        if level == "Info":
            self.info.setStyleSheet("background-color: rgb(50,100,50)")
        elif level == "Warning":
            self.info.setStyleSheet("background-color: rgb(100,100,50)")
        elif level == "Error":
            self.info.setStyleSheet("background-color: rgb(100,50,50)")
        elif level == "Clear":
            self.info.setStyleSheet("background-color: rgb(50,50,50)")

        self.info.setCursorPosition(0)

    def update_status(self, status: Status):
        pass


class LabledToolbar(Toolbar):
    def __init__(
        self,
        label: str,
        thickness: int = 30,
        direction: ToolbarDirection = ToolbarDirection.Horizontal,
        parent: QWidget | None = None,
    ):
        self.label_str = label
        super().__init__(direction, thickness, parent)

    @override
    def init_widgets(self):
        super().init_widgets()
        self.label = QLabel(self.label_str)

    @override
    def init_layouts(self):
        super().init_layouts()
        self.add_widget(self.label)

    @override
    def init_signals(self):
        super().init_signals()


class AssetToolbar(LabledToolbar):
    add = Signal()
    remove = Signal()
    open = Signal()
    pool_changed = Signal(Path)

    def __init__(
        self,
        label: str,
        pool: PoolManager,
        thickness: int = 30,
        direction: ToolbarDirection = ToolbarDirection.Horizontal,
        parent: QWidget | None = None,
    ):
        self.pool = pool
        super().__init__(label, thickness, direction, parent)

    @override
    def init_widgets(self):
        super().init_widgets()
        self.dropdown = QComboBox()
        self._pools: dict[str, Path] = {}

        size = (30, 30)
        self.add_folder = IconButton(size)
        self.add_folder.set_icon(":icons/tabler-icon-folder-plus.png")
        self.remove_folder = IconButton(size)
        self.remove_folder.set_icon(":icons/tabler-icon-folder-minus.png")
        self.open_folder = IconButton(size)
        self.open_folder.set_icon(":icons/tabler-icon-folder-open.png")

        self._load_pools()

    @override
    def init_layouts(self):
        super().init_layouts()
        self.main_layout.addWidget(self.dropdown)
        self.main_layout.addWidget(self.add_folder)
        self.main_layout.addWidget(self.remove_folder)
        self.main_layout.addWidget(self.open_folder)
        self.main_layout.addWidget(VLine())

    @override
    def init_signals(self):
        super().init_signals()
        self.add_folder.clicked.connect(lambda: self.add.emit())
        self.remove_folder.clicked.connect(lambda: self.remove.emit())
        self.open_folder.clicked.connect(lambda: self.open.emit())
        self.add_folder.clicked.connect(self.open_add_dialog)
        self.remove_folder.clicked.connect(self.open_delete_dialog)
        self.open_folder.clicked.connect(lambda: self.pool.open_dir(self.current_pool))
        self.dropdown.currentTextChanged.connect(
            lambda: self.pool_changed.emit(self.current_pool)
        )

    @property
    def current_pool(self) -> Optional[Path]:
        text = self.dropdown.currentText()
        return self._pools.get(text)

    def open_add_dialog(self):
        create_dialog = CreatePoolDialog()
        create_dialog.pool_created.connect(self.new_pool)
        create_dialog.exec()

    def new_pool(self, data: tuple[str, Path]):
        name, path = data
        name, path = self.pool.new(name, path)

        self.dropdown.addItem(name)
        self.dropdown.setCurrentText(name)
        self._pools[name] = path

    def open_delete_dialog(self):
        dialog = DeletePoolDialog()
        dialog.pool_deleted.connect(self.pool.delete)

    def _load_pools(self):
        items = self.pool.get()
        self.dropdown.addItems(tuple(items.keys()))
        self._pools = items


class MultiToolbar(QWidget):
    def __init__(
        self,
        direction: ToolbarDirection,
        multibars: dict[str, AssetToolbar],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.multibars = multibars
        self.direction = direction
        self.thickness = (
            next(iter(self.multibars.values())).thickness if len(multibars) > 0 else 30
        )
        self.current = next(iter(self.multibars.values()))

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

        if len(multibars) > 0:
            self.set_current(next(iter(self.multibars)))

    def init_widgets(self):
        if self.direction == ToolbarDirection.Horizontal:
            self.setFixedHeight(self.thickness)
        elif self.direction == ToolbarDirection.Vertical:
            self.setFixedWidth(self.thickness)

    def init_layouts(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

    def init_signals(self):
        pass

    def _clear_layout(self):
        while self.main_layout.count():
            widget = self.main_layout.takeAt(0).widget()
            widget.setParent(None)

    def set_current(self, toolbar_id: str) -> Optional[Toolbar]:
        if toolbar_id not in self.multibars.keys():
            return None

        self._clear_layout()
        self.current = self.multibars[toolbar_id]
        self.main_layout.addWidget(self.current)


class ModelToolbar(AssetToolbar):
    def __init__(
        self,
        pool: PoolManager,
        label: str = "Model",
        thickness: int = 40,
        direction: ToolbarDirection = ToolbarDirection.Horizontal,
        parent: QWidget | None = None,
    ):
        super().__init__(label, pool, thickness, direction, parent)

    @override
    def init_widgets(self):
        super().init_widgets()
        self.export_btn = IconButton((30, 30))
        self.export_btn.set_icon(":icons/tabler-icon-package-export.png")
        self.export_btn.set_tooltip("Export Model")

    @override
    def init_layouts(self):
        super().init_layouts()

        self.add_widgets([self.export_btn], stretch=True)

    @override
    def init_signals(self):
        super().init_signals()
        self.export_btn.clicked.connect(self.export_dialog)

    def export_dialog(self):
        dialog = ExportModelDialog()
        dialog.finished.connect(self.on_export_dialog_finished)
        dialog.exec()

    def on_export_dialog_finished(self, data: ExportModelDialog.Data):
        if not self.current_pool:
            Logger.error("No current pool selected for export.")
            return

        name = data["name"]
        ext = data["ext"]
        export_type = data["export_type"]
        copy_textures = data["copy_textures"]

        file_dir = self.current_pool / name
        file_dir.mkdir(parents=True, exist_ok=True)
        file_path = file_dir / f"{name}.{ext}"

        if export_type == ExportModelDialog.ExportType.SAVE:
            self.pool.save(file_path)
        elif export_type == ExportModelDialog.ExportType.EXPORT:
            self.pool.export(file_path)

        if copy_textures:
            self.pool.copy_textures(file_path)


class MaterialToolbar(AssetToolbar):
    def __init__(
        self,
        pool: PoolManager,
        label: str = "Materials",
        thickness: int = 40,
        direction: ToolbarDirection = ToolbarDirection.Horizontal,
        parent: QWidget | None = None,
    ):
        super().__init__(label, pool, thickness, direction, parent)

    @override
    def init_widgets(self):
        super().init_widgets()

    @override
    def init_layouts(self):
        super().init_layouts()
        self.add_widgets([], stretch=True)

    @override
    def init_signals(self):
        super().init_signals()
