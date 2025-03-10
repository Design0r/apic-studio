from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget

from apic_studio.core import Logger
from apic_studio.core.asset_loader import Asset, AsyncAssetLoader
from apic_studio.ui.buttons import ViewportButton
from apic_studio.ui.flow_layout import FlowLayout


class MainWindow(QWidget):
    win_instance = None

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._widgets: dict[Path, ViewportButton] = {}
        self.setWindowTitle("Apic Studio")
        self.setWindowIcon(QIcon(":icons/tabler-icon-packages.png"))
        self.setWindowFlag(Qt.WindowType.Window)

        # Logger.write_to_file(self.settings.LOGGING_PATH)
        Logger.set_propagate(False)
        Logger.info("starting Apic Studio...")

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

    @classmethod
    def show_window(cls) -> MainWindow:
        if not cls.win_instance:
            cls.win_instance = MainWindow()
            cls.win_instance.show()
        elif cls.win_instance.isHidden():
            cls.win_instance.show()
        else:
            cls.win_instance.showNormal()

        return cls.win_instance

    def init_widgets(self):
        self.setGeometry(300, 300, 300, 400)

    def init_layouts(self):
        self.main_layout = FlowLayout(self)
        self.al = AsyncAssetLoader()
        self.al.asset_loaded.connect(self.replace_icon)

        for x in Path(
            "/Users/alex/GitHub/apic-studio/apic_studio/resource/icons/"
        ).iterdir():
            b = ViewportButton(x, (200, 200))
            self._widgets[x] = b
            self.main_layout.addWidget(b)
            self.al.load_asset_async(x)

    def replace_icon(self, asset: Asset):
        print(f"asset {asset.name}")
        w = self._widgets[asset.path]
        w.icon.setIcon(asset.icon)
        w.repaint()

    def init_signals(self):
        pass
