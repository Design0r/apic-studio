from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, override

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import QHBoxLayout, QSplitter, QVBoxLayout, QWidget

from apic_studio import __version__
from apic_studio.core.settings import SettingsManager
from apic_studio.services import AssetLoader, DCCBridge, Screenshot, pools
from apic_studio.ui.attribute_editor import AttributeEditor
from apic_studio.ui.buttons import ViewportButton
from apic_studio.ui.toolbar import (
    HdriToolbar,
    MaterialToolbar,
    ModelToolbar,
    MultiToolbar,
    Sidebar,
    Statusbar,
    ToolbarDirection,
)
from apic_studio.ui.viewport import Viewport


class MainWindow(QWidget):
    win_instance = None

    def __init__(
        self,
        dcc: DCCBridge,
        settings: SettingsManager,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._widgets: dict[Path, ViewportButton] = {}
        self.settings = settings
        self.loader = AssetLoader()
        self.screenshot = Screenshot()
        self.dcc = dcc

        self.vp_map: dict[str, Any] = {
            "materials": self.settings.MaterialSettings,
            "models": self.settings.ModelSettings,
            "lightsets": self.settings.LightsetSettings,
            "hdris": self.settings.HdriSettings,
        }

        self.setWindowTitle(f"Apic Studio - {__version__}")
        self.setWindowIcon(QIcon(":icons/apic_logo.png"))
        self.setWindowFlag(Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("QWidget {background-color: #444; color: #fff}")

        self.init_widgets()
        self.init_layouts()

        self.set_view(self.settings.WindowSettings.current_viewport, draw=False)
        self.init_signals()

    def init_widgets(self):
        self.setGeometry(*self.settings.WindowSettings.window_geometry)

        self.sidebar = Sidebar(40)
        self.sidebar.highlight_modes(self.settings.WindowSettings.current_viewport)

        self.model_tb = ModelToolbar(pools.ModelPoolManager(), self.dcc)
        self.model_tb.set_current_pool(self.settings.ModelSettings.current_pool)
        self.material_tb = MaterialToolbar(pools.MaterialPoolManager(), self.dcc)
        self.material_tb.set_current_pool(self.settings.MaterialSettings.current_pool)
        self.lightset_tb = ModelToolbar(
            pools.LightsetPoolManager(), self.dcc, label="Lightsets"
        )
        self.lightset_tb.set_current_pool(self.settings.LightsetSettings.current_pool)
        self.hdri_tb = HdriToolbar(pools.HdriPoolManager(), self.dcc)
        self.hdri_tb.set_current_pool(self.settings.HdriSettings.current_pool)

        self.toolbar = MultiToolbar(
            ToolbarDirection.Horizontal,
            {
                "materials": self.material_tb,
                "models": self.model_tb,
                "lightsets": self.lightset_tb,
                "hdris": self.hdri_tb,
            },
        )
        self.viewport = Viewport(self.dcc, self.settings, self.loader, self.screenshot)
        self.attrib_editor = AttributeEditor()

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setOpaqueResize(True)
        self.splitter.addWidget(self.viewport)
        self.splitter.addWidget(self.attrib_editor)

        self.status = Statusbar(30)

    def init_layouts(self):
        self.vp_layout = QVBoxLayout()
        self.vp_layout.setContentsMargins(0, 0, 0, 0)
        self.vp_layout.addWidget(self.toolbar)
        self.vp_layout.addWidget(self.splitter)
        self.vp_layout.addWidget(self.status)

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addLayout(self.vp_layout)
        # self.splitter.setSizes([0, 1])
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)

    def init_signals(self):
        s = self.sidebar
        s.models.clicked.connect(lambda: self.set_view("models"))
        s.materials.clicked.connect(lambda: self.set_view("materials"))
        s.lightsets.clicked.connect(lambda: self.set_view("lightsets"))
        s.hdris.clicked.connect(lambda: self.set_view("hdris"))
        self.dcc.on_connect(s.conn_btn.set_connected)
        self.dcc.on_disconnect(s.conn_btn.set_disconnected)
        s.conn_btn.clicked.connect(
            lambda: self.dcc.connect(self.settings.CoreSettings.address)
        )
        self.viewport.asset_clicked.connect(self.attrib_editor.load.emit)
        self.material_tb.render_previews.connect(self.render_previews)

        for t in self.toolbar.multibars.values():
            t.pool_changed.connect(self.draw)
            t.asset_changed.connect(self.loader.load_asset)

    def closeEvent(self, event: QCloseEvent) -> None:
        geo = self.geometry()
        self.settings.WindowSettings.window_geometry = [
            geo.x(),
            geo.y(),
            geo.width(),
            geo.height(),
        ]
        self.loader.stop()
        self.viewport.shutdown()
        self.settings.WindowSettings.current_viewport = self.viewport.curr_view
        return super().closeEvent(event)

    def set_view(self, view: str, draw: bool = True, ignore_signals: bool = False):
        self.viewport.set_current_view(view)
        self.toolbar.set_current_view(view)
        if draw:
            self.draw()

    def draw(self, curr_pool: Optional[Path] = None, force: bool = False):
        if curr_pool:
            self.viewport.draw(curr_pool, force=force)
        else:
            curr_pool = self.toolbar.current.current_pool
            if not curr_pool:
                return
            self.viewport.draw(curr_pool, force=force)

        self.vp_map[self.viewport.curr_view].current_pool = curr_pool.parent.stem

    @override
    def show(self):
        super().show()
        self.draw()

    def render_previews(self):
        materials = [m for w in self.viewport.widgets.values() if (m := w.file)]
        self.dcc.materials_preview_create_all(
            materials, callback=lambda: self.draw(force=True)
        )
