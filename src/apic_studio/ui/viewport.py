from __future__ import annotations

import shutil
from functools import partial
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QHBoxLayout, QMenu, QScrollArea, QVBoxLayout, QWidget

from apic_studio.core.asset_loader import Asset, AssetLoader
from apic_studio.core.settings import SettingsManager
from apic_studio.ui.buttons import ViewportButton
from apic_studio.ui.flow_layout import FlowLayout
from shared.logger import Logger
from shared.messaging import Message
from shared.network import Connection


class Viewport(QWidget):
    def __init__(
        self,
        ctx: Connection,
        settings: SettingsManager,
        loader: AssetLoader,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._widgets: dict[str, ViewportButton] = {}
        self.loader = loader
        self.settings = settings
        self.ctx = ctx
        self.cache: dict[str, dict[str, Asset]] = {
            "models": {},
            "materials": {},
            "hdris": {},
        }
        self.curr_view = "models"

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

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

    def init_signals(self):
        self.loader.asset_loaded.connect(self.on_asset_load)

    def on_asset_load(self, asset: Asset):
        w = self._widgets[asset.path.stem]
        w.set_thumbnail(asset.icon, 200)
        w.set_filesize(asset.size)
        w.set_filetype(asset.suffix)
        w.file = asset.path
        self.flow_layout.addWidget(w)

    def send_msg(self, msg: Message):
        self.ctx.send_recv(msg)

    def _clear_layout(self):
        while self.flow_layout.count():
            w = self.flow_layout.takeAt(0).widget()
            w.setParent(None)

    def draw(self, path: Path):
        self._clear_layout()

        Logger.debug(f"drawing called: {path}")
        if not path:
            return

        for x in path.iterdir():
            if cached_widget := self._widgets.get(x.stem):
                self.flow_layout.addWidget(cached_widget)
                continue

            b = ViewportButton(x, (200, 200))
            b.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            b.customContextMenuRequested.connect(partial(self.on_context_menu, b))
            self._widgets[x.stem] = b
            self.loader.load_asset(x)

    def set_current(self, view: str):
        if view not in self.cache:
            return

        self.curr_view = view
        self._clear_layout()

    def on_context_menu(self, btn: ViewportButton, point: QPoint):
        import_act = QAction("Import")
        import_act.triggered.connect(
            lambda: self.send_msg(Message("models.import", {"path": str(btn.file)}))
        )
        delete_act = QAction("Delete")
        delete_act.triggered.connect(lambda: self.delete_widget(btn))

        menu = QMenu()
        menu.addAction(import_act)
        menu.addSeparator()
        menu.addAction(delete_act)

        menu.exec_(btn.mapToGlobal(point))

    def delete_widget(self, btn: ViewportButton):
        if btn.file.is_dir():
            shutil.rmtree(btn.file, ignore_errors=True)
        else:
            btn.file.unlink(missing_ok=True)

        if btn.file.stem in self._widgets:
            del self._widgets[btn.file.stem]
        btn.setParent(None)
        btn.deleteLater()
