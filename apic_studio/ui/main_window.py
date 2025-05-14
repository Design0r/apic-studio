from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from apic_studio import __version__
from apic_studio.core.asset_loader import AssetLoader
from apic_studio.core.settings import SettingsManager
from apic_studio.messaging.message import Message
from apic_studio.network import Connection
from apic_studio.services import pools
from apic_studio.ui.buttons import ViewportButton
from apic_studio.ui.toolbar import (
    MaterialToolbar,
    ModelToolbar,
    MultiToolbar,
    Sidebar,
    ToolbarDirection,
)
from apic_studio.ui.viewport import Viewport


class MainWindow(QWidget):
    win_instance = None

    def __init__(
        self,
        ctx: Connection,
        settings: SettingsManager,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._widgets: dict[Path, ViewportButton] = {}
        self.settings = settings
        self.loader = AssetLoader()
        self.ctx = ctx

        self.setWindowTitle(f"Apic Studio - {__version__}")
        self.setWindowIcon(QIcon(":icons/tabler-icon-packages.png"))
        self.setWindowFlag(Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("QWidget {background-color: #444}")

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

        self.draw()

    def init_widgets(self):
        self.setGeometry(*self.settings.WindowSettings.window_geometry)

        self.sidebar = Sidebar(40)
        self.sidebar.highlight_modes(1)

        self.model_tb = ModelToolbar(pools.ModelPoolManager())
        self.material_tb = MaterialToolbar(pools.MaterialPoolManager())

        self.toolbar = MultiToolbar(
            ToolbarDirection.Horizontal,
            {"materials": self.material_tb, "models": self.model_tb},
        )
        self.viewport = Viewport(self.ctx, self.settings, self.loader)
        self.model_tb.add_folder.clicked.connect(
            lambda: self.viewport.send_msg(Message("models.export.selected"))
        )

    def init_layouts(self):
        self.vp_layout = QVBoxLayout()
        self.vp_layout.setContentsMargins(0, 0, 0, 0)
        self.vp_layout.addWidget(self.toolbar)
        self.vp_layout.addWidget(self.viewport)

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addLayout(self.vp_layout)

    def init_signals(self):
        s = self.sidebar
        s.models.clicked.connect(lambda: self.set_view("models"))
        s.materials.clicked.connect(lambda: self.set_view("materials"))
        self.ctx.on_connect(lambda: s.conn_btn.setText("C"))
        self.ctx.on_disconnect(lambda: s.conn_btn.setText("D"))
        s.conn_btn.clicked.connect(
            lambda: self.ctx.connect(self.settings.WindowSettings.address)
        )

        for t in self.toolbar.multibars.values():
            t.pool_changed.connect(self.viewport.draw)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.settings.WindowSettings.window_geometry = [
            self.x(),
            self.y(),
            self.width(),
            self.height(),
        ]
        self.loader.stop()
        return super().closeEvent(event)

    def set_view(self, view: str):
        self.toolbar.set_current(view)
        self.viewport.set_current(view)
        self.draw()

    def draw(self):
        curr_pool = self.toolbar.current.current_pool
        if not curr_pool:
            return
        self.viewport.draw(curr_pool)
