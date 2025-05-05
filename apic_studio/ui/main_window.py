from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from apic_studio.core.asset_loader import AssetLoader
from apic_studio.core.settings import SettingsManager
from apic_studio.network import Connection
from apic_studio.ui.buttons import ViewportButton
from apic_studio.ui.toolbar import MultiToolbar, Sidebar, Toolbar, ToolbarDirection
from apic_studio.ui.viewport import Viewport


class MainWindow(QWidget):
    win_instance = None

    def __init__(
        self,
        ctx: Connection,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._widgets: dict[Path, ViewportButton] = {}
        self.settings = SettingsManager()
        self.loader = AssetLoader()
        self.ctx = ctx

        self.setWindowTitle("Apic Studio")
        self.setWindowIcon(QIcon(":icons/tabler-icon-packages.png"))
        self.setWindowFlag(Qt.WindowType.Window)

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

    def init_widgets(self):
        self.setGeometry(*self.settings.WindowSettings.window_geometry)

        self.sidebar = Sidebar(40)
        self.sidebar.highlight_modes(1)

        self.model_tb = Toolbar(ToolbarDirection.Horizontal, 30)
        self.model_tb.add_widget(QPushButton("Models"))

        self.material_tb = Toolbar(ToolbarDirection.Horizontal, 30)
        self.material_tb.add_widget(QPushButton("Materials"))

        self.toolbar = MultiToolbar(
            ToolbarDirection.Horizontal,
            {"materials": self.material_tb, "models": self.model_tb},
        )
        self.viewport = Viewport(self.ctx, self.settings)

    def init_layouts(self):
        self.vp_layout = QVBoxLayout()
        self.vp_layout.addWidget(self.toolbar)
        self.vp_layout.addWidget(self.viewport)

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addLayout(self.vp_layout)

    def init_signals(self):
        s = self.sidebar
        s.models.clicked.connect(lambda: self.toolbar.set_current("models"))
        s.materials.clicked.connect(lambda: self.toolbar.set_current("materials"))

    def closeEvent(self, event: QCloseEvent) -> None:
        self.settings.WindowSettings.window_geometry = [
            self.x(),
            self.y(),
            self.width(),
            self.height(),
        ]
        self.loader.stop()
        return super().closeEvent(event)
