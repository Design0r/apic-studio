from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QWidget

from apic_studio.core.asset_loader import Asset, AssetLoader
from apic_studio.core.settings import SettingsManager
from apic_studio.ui.buttons import ViewportButton
from apic_studio.ui.flow_layout import FlowLayout


class MainWindow(QWidget):
    win_instance = None

    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._widgets: dict[Path, ViewportButton] = {}
        self.settings = SettingsManager()
        self.loader = AssetLoader()

        self.setWindowTitle("Apic Studio")
        self.setWindowIcon(QIcon(":icons/tabler-icon-packages.png"))
        self.setWindowFlag(Qt.WindowType.Window)

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
        self.setGeometry(*self.settings.WindowSettings.window_geometry)

    def init_layouts(self):
        self.flow_layout = FlowLayout(self.grid_widget)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.scroll_area)

    def replace_icon(self, asset: Asset):
        w = self._widgets[asset.path]
        w.icon.setIcon(asset.icon)
        w.icon.setIconSize(QSize(200, 200))

    def init_signals(self):
        self.loader.asset_loaded.connect(self.replace_icon)

    def closeEvent(self, event: QCloseEvent) -> None:
        self.settings.WindowSettings.window_geometry = [
            self.x(),
            self.y(),
            self.width(),
            self.height(),
        ]
        self.loader.stop()
        return super().closeEvent(event)

    def draw(self):
        for x in (self.settings.ROOT_PATH / "apic_studio/resource/icons").iterdir():
            b = ViewportButton(x, (200, 200))
            self._widgets[x] = b
            self.flow_layout.addWidget(b)
            self.loader.load_asset(x)
