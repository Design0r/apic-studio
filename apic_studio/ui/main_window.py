from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import QWidget

from apic_studio.core.asset_loader import Asset, AssetLoader
from apic_studio.core.settings import SettingsManager
from apic_studio.ui.buttons import ViewportButton
from apic_studio.ui.flow_layout import FlowLayout


class MainWindow(QWidget):
    win_instance = None

    def __init__(self, settings: SettingsManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._widgets: dict[Path, ViewportButton] = {}
        self.settings = settings

        self.setWindowTitle("Apic Studio")
        self.setWindowIcon(QIcon(":icons/tabler-icon-packages.png"))
        self.setWindowFlag(Qt.WindowType.Window)

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

    @classmethod
    def show_window(cls, settings: SettingsManager) -> MainWindow:
        if not cls.win_instance:
            cls.win_instance = MainWindow(settings)
            cls.win_instance.show()
        elif cls.win_instance.isHidden():
            cls.win_instance.show()
        else:
            cls.win_instance.showNormal()

        return cls.win_instance

    def init_widgets(self):
        self.setGeometry(300, 300, 1000, 700)

    def init_layouts(self):
        self.main_layout = FlowLayout(self)
        self.al = AssetLoader()
        self.al.asset_loaded.connect(self.replace_icon)

        for x in (self.settings.ROOT_PATH / "apic_studio/resource/icons").iterdir():
            b = ViewportButton(x, (200, 200))
            self._widgets[x] = b
            self.main_layout.addWidget(b)
            self.al.load_asset(x)

    def replace_icon(self, asset: Asset):
        print(f"asset {asset.name}")
        w = self._widgets[asset.path]
        w.icon.setIcon(asset.icon)
        w.icon.setIconSize(QSize(200, 200))

    def init_signals(self):
        pass

    def closeEvent(self, event: QCloseEvent) -> None:
        self.al.stop()
        return super().closeEvent(event)
