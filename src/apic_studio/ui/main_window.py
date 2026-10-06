from __future__ import annotations

from pathlib import Path
from typing import Any, override

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from apic_studio import __version__
from apic_studio.core.settings import SettingsManager
from apic_studio.services import AssetLoader, DCCBridge, Screenshot, pools
from apic_studio.services.tags import tag_events
from apic_studio.ui.attribute_editor import AttributeEditor
from apic_studio.ui.splitter import PanelSplitter
from apic_studio.ui.toolbar import (
    HdriToolbar,
    MaterialToolbar,
    ModelToolbar,
    MultiToolbar,
    Sidebar,
    Statusbar,
    TextureToolbar,
    ToolbarDirection,
    UtilityToolbar,
)
from apic_studio.ui.viewport import Viewport


class MainWindow(QWidget):
    win_instance = None

    def __init__(
        self,
        dcc: DCCBridge,
        settings: SettingsManager,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.settings = settings
        self.loader = AssetLoader()
        self.screenshot = Screenshot()
        self.dcc = dcc

        self.vp_map: dict[str, Any] = {
            "materials": self.settings.MaterialSettings,
            "models": self.settings.ModelSettings,
            "apic_models": self.settings.ApicModelSettings,
            "lightsets": self.settings.LightsetSettings,
            "hdris": self.settings.HdriSettings,
            "textures": self.settings.TextureSettings,
            "utilities": self.settings.UtilitySettings,
        }

        self.setWindowTitle(f"Apic Studio - {__version__}")
        self.setWindowIcon(QIcon(":icons/apic_logo.png"))
        self.setWindowFlag(Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("QWidget {background-color: #444; color: #fff}")

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

        self.set_view(self.settings.WindowSettings.current_viewport, draw=False)

    def init_widgets(self):
        self.setGeometry(*self.settings.WindowSettings.window_geometry)

        self.sidebar = Sidebar(40)
        self.sidebar.highlight_modes(self.settings.WindowSettings.current_viewport)

        self.model_tb = ModelToolbar(pools.ModelPoolManager(), self.dcc)
        self.model_tb.set_current_pool(self.settings.ModelSettings.current_pool)
        self.apic_model_tb = ModelToolbar(
            pools.ApicModelPoolManager(), self.dcc, label="Apic Models"
        )
        self.apic_model_tb.set_current_pool(
            self.settings.ApicModelSettings.current_pool
        )
        self.material_tb = MaterialToolbar(pools.MaterialPoolManager(), self.dcc)
        self.material_tb.set_current_pool(self.settings.MaterialSettings.current_pool)
        self.lightset_tb = ModelToolbar(
            pools.LightsetPoolManager(), self.dcc, label="Lightsets"
        )
        self.lightset_tb.set_current_pool(self.settings.LightsetSettings.current_pool)
        self.hdri_tb = HdriToolbar(pools.HdriPoolManager(), self.dcc)
        self.hdri_tb.set_current_pool(self.settings.HdriSettings.current_pool)

        self.textures_tb = TextureToolbar(pools.TexturePoolManager(), self.dcc)
        self.textures_tb.set_current_pool(self.settings.TextureSettings.current_pool)

        self.utility_tb = UtilityToolbar(pools.UtilityPoolManager(), self.dcc)
        self.utility_tb.set_current_pool(self.settings.UtilitySettings.current_pool)

        self.toolbar = MultiToolbar(
            ToolbarDirection.Horizontal,
            {
                "materials": self.material_tb,
                "models": self.model_tb,
                "apic_models": self.apic_model_tb,
                "lightsets": self.lightset_tb,
                "hdris": self.hdri_tb,
                "textures": self.textures_tb,
                "utilities": self.utility_tb,
            },
        )
        self.viewport = Viewport(self.dcc, self.settings, self.loader, self.screenshot)
        self.attrib_editor = AttributeEditor()

        self.splitter = PanelSplitter(self.viewport, self.attrib_editor)
        self.toggle_details = QShortcut(QKeySequence("Ctrl+I"), self)

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

        # lay out now, so the restored width applies to the real window size
        # rather than being scaled from the splitter's default one
        self.main_layout.activate()
        win = self.settings.WindowSettings
        self.splitter.set_panel(win.details_visible, win.details_width or None)

    def init_signals(self):
        s = self.sidebar
        s.textures.clicked.connect(lambda: self.set_view("textures"))
        s.models.clicked.connect(lambda: self.set_view("models"))
        s.apic_models.clicked.connect(lambda: self.set_view("apic_models"))
        s.materials.clicked.connect(lambda: self.set_view("materials"))
        s.lightsets.clicked.connect(lambda: self.set_view("lightsets"))
        s.hdris.clicked.connect(lambda: self.set_view("hdris"))
        s.utilities.clicked.connect(lambda: self.set_view("utilities"))
        self.dcc.on_connect(s.conn_btn.connected.emit)
        self.dcc.on_disconnect(s.conn_btn.disconnected.emit)
        s.conn_btn.clicked.connect(
            lambda: self.dcc.connect(self.settings.CoreSettings.address)
        )
        self.viewport.asset_clicked.connect(self.attrib_editor.load.emit)
        self.material_tb.render_previews.connect(self.render_previews)
        self.toggle_details.activated.connect(self.splitter.toggle_panel)
        self.attrib_editor.tags_updated.connect(self.viewport.update_asset_tags)
        self.attrib_editor.tag_filter_requested.connect(self.filter_by_tag)
        tag_events.rewritten.connect(self.on_tag_rewritten)

        for t in self.toolbar.multibars.values():
            t.pool_changed.connect(self.draw)
            t.asset_changed.connect(self.loader.load_asset)
            t.force_refresh.connect(lambda x: self.draw(x, force=True))  # type: ignore
            t.search_text_changed.connect(
                lambda x: self.draw(x[0], filter=x[1])  # type: ignore
            )
            t.tag_filter_changed.connect(lambda _: self.apply_tag_filter())

    def closeEvent(self, event: QCloseEvent) -> None:
        geo = self.geometry()
        self.settings.WindowSettings.window_geometry = [
            geo.x(),
            geo.y(),
            geo.width(),
            geo.height(),
        ]
        self.settings.WindowSettings.details_width = self.splitter.panel_width
        self.settings.WindowSettings.details_visible = self.splitter.is_panel_open()
        self.attrib_editor.flush()
        self.loader.stop()
        self.viewport.shutdown()
        self.settings.WindowSettings.current_viewport = self.viewport.curr_view
        return super().closeEvent(event)

    def set_view(self, view: str, draw: bool = True):
        self.viewport.set_current_view(view)
        self.toolbar.set_current_view(view)
        self.toolbar.current.set_current_pool(
            self.vp_map[view].current_pool, blockSignals=True
        )
        self.apply_tag_filter()

        if draw:
            self.draw()

    def draw(
        self,
        curr_pool: Path | None = None,
        force: bool = False,
        filter: str | None = None,
    ):
        if not curr_pool:
            curr_pool = self.toolbar.current.current_pool
            if not curr_pool:
                self.viewport.clear()
                return

        if curr_pool == Path():
            self.viewport.clear()
            return

        if filter is None:
            # a pool switch keeps whatever the searchbar still shows
            filter = self.toolbar.current.search_text()

        self.viewport.draw(curr_pool, force=force, filter=filter)
        self.vp_map[self.viewport.curr_view].current_pool = curr_pool.parent.stem

    @override
    def show(self):
        super().show()
        self.draw()

    def apply_tag_filter(self):
        tags, match_all = self.toolbar.current.tag_filter.selection()
        self.viewport.set_tag_filter(tags, match_all)

    def filter_by_tag(self, tag: str):
        self.toolbar.current.tag_filter.set_selected([tag])

    def on_tag_rewritten(self, old: str, new: str | None):
        self.viewport.invalidate_tag_index()
        for t in self.toolbar.multibars.values():
            t.tag_filter.rename_tag(old, new)

    def render_previews(self):
        materials = self.viewport.asset_files()
        self.dcc.materials_preview_create_all(
            materials, callback=lambda: self.draw(force=True)
        )
