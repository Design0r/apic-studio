from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QHBoxLayout, QMenu, QScrollArea, QVBoxLayout, QWidget

from apic_studio.core.settings import SettingsManager
from apic_studio.services import Asset, AssetLoader, DCCBridge, Screenshot
from apic_studio.ui.buttons import ViewportButton
from apic_studio.ui.flow_layout import FlowLayout
from shared.logger import Logger


class Viewport(QWidget):
    asset_clicked = Signal(Asset)

    def __init__(
        self,
        dcc: DCCBridge,
        settings: SettingsManager,
        loader: AssetLoader,
        screenshot: Screenshot,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.loader = loader
        self.settings = settings
        self.screenshot = screenshot
        self.dcc = dcc
        self._widgets: dict[str, dict[str, ViewportButton]] = {
            "models": {},
            "materials": {},
            "hdris": {},
            "lightsets": {},
        }
        self.curr_view = "materials"
        self.curr_pool: Path

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
        self.screenshot.created.connect(self.loader.load_asset)

    @property
    def widgets(self) -> dict[str, ViewportButton]:
        return self._widgets[self.curr_view]

    def on_asset_load(self, asset: Asset):
        w = self.widgets[asset.path.stem]
        w.set_thumbnail(asset.icon, 185)
        w.set_file(asset.file, asset.size, asset.suffix)
        w.file = asset.file
        self.flow_layout.addWidget(w)
        w.clicked.connect(lambda: self.asset_clicked.emit(asset))

    def _clear_layout(self):
        while self.flow_layout.count():
            item = self.flow_layout.takeAt(0)
            if not item:
                continue
            item.widget().setParent(None)

    def draw(self, path: Path):
        self._clear_layout()

        Logger.debug(f"drawing called: {path}")
        if not path:
            return

        self.curr_pool = path.parent

        for x in path.iterdir():
            if not self.loader.is_asset(x):
                continue

            if cached_widget := self.widgets.get(x.stem):
                self.flow_layout.addWidget(cached_widget)
                continue

            b = ViewportButton(x, (200, 200))
            b.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            b.customContextMenuRequested.connect(partial(self.on_context_menu, b))
            self.widgets[x.stem] = b
            self.loader.load_asset(x)

    def set_current_view(self, view: str):
        if view not in self._widgets:
            return

        self.curr_view = view
        self._clear_layout()

    def on_context_menu(self, btn: ViewportButton, point: QPoint):
        open_act = QAction("Open")
        open_act.triggered.connect(lambda: self.dcc.file_open(btn.file))

        import_act = QAction("Import")
        import_as_area = QAction("Import as Arealight")
        import_as_area.triggered.connect(lambda: self.dcc.hdri_import_as_area(btn.file))

        if self.curr_view == "models":
            import_act.triggered.connect(lambda: self.dcc.models_import(btn.file))
        elif self.curr_view == "materials":
            import_act.triggered.connect(lambda: self.dcc.materials_import(btn.file))
        elif self.curr_view == "hdris":
            import_act.setText("Import as Domelight")
            import_act.triggered.connect(lambda: self.dcc.hdri_import_as_dome(btn.file))

        render_act = QAction("Render Preview")
        render_act.triggered.connect(lambda: self.on_render(btn))

        screenshot_act = QAction("Create Screenshot")
        screenshot_act.triggered.connect(lambda: self.screenshot.show_dialog(btn.file))

        delete_act = QAction("Delete")
        delete_act.triggered.connect(lambda: self.delete_widget(btn))

        menu = QMenu()

        if self.curr_view not in ("hdris", "utils"):
            menu.addAction(open_act)

        menu.addAction(import_act)

        if self.curr_view == "hdris":
            menu.addAction(import_as_area)

        menu.addSeparator()

        if self.curr_view in ("models", "lightsets"):
            menu.addAction(screenshot_act)

        if self.curr_view == "materials":
            menu.addAction(render_act)

        menu.addSeparator()
        menu.addAction(delete_act)

        menu.exec_(btn.mapToGlobal(point))

    def on_render(self, btn: ViewportButton):
        self.dcc.materials_preview_create(btn.file)
        self.loader.load_asset(btn.file.parent, refresh=True)

    def delete_widget(self, btn: ViewportButton):
        del self.widgets[btn.file.stem]
        btn.setParent(None)
        btn.deleteLater()
