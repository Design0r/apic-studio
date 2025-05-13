from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QHBoxLayout, QScrollArea, QVBoxLayout, QWidget

from apic_studio.core.asset_loader import Asset, AssetLoader
from apic_studio.core.settings import SettingsManager
from apic_studio.messaging import Message
from apic_studio.network import Connection
from apic_studio.ui.buttons import ViewportButton
from apic_studio.ui.flow_layout import FlowLayout


class Viewport(QWidget):
    def __init__(
        self,
        ctx: Connection,
        settings: SettingsManager,
        loader: AssetLoader,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._widgets: dict[Path, ViewportButton] = {}
        self.loader = loader
        self.settings = settings
        self.ctx = ctx
        self.cache: dict[str, dict[Path, Asset]] = {
            "models": {},
            "materials": {},
            "hdris": {},
        }
        self.curr_view = "models"

        self.init_widgets()
        self.init_layouts()
        self.init_signals()
        self.draw()

    def init_widgets(self):
        self.grid_widget = QWidget()
        self.scroll_area = QScrollArea()
        self.scroll_area.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self.scroll_area.setWidget(self.grid_widget)

    def init_layouts(self):
        self.flow_layout = FlowLayout(self.grid_widget)
        self.vp_layout = QVBoxLayout()

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 0, 0)
        self.main_layout.addWidget(self.scroll_area)

    def replace_icon(self, asset: Asset):
        w = self._widgets[asset.path]
        w.icon.setIcon(asset.icon)
        w.icon.setIconSize(QSize(200, 200))

    def init_signals(self):
        self.loader.asset_loaded.connect(self.replace_icon)

    def send_msg(self, msg: Message):
        self.ctx.send_recv(msg)

    def _clear_layout(self):
        while self.flow_layout.count():
            w = self.flow_layout.takeAt(0).widget()
            w.setParent(None)

    def draw(self):
        for x in (self.settings.ROOT_PATH / "apic_studio/resources/icons").iterdir():
            b = ViewportButton(x, (200, 200))
            self._widgets[x] = b
            self.flow_layout.addWidget(b)
            self.loader.load_asset(x)

    def set_current(self, view: str):
        if view not in self.cache:
            return

        self.curr_view = view
        self._clear_layout()
        self.draw()
