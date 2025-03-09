from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QPushButton, QWidget

from apic_studio.core import Logger
from apic_studio.ui.flow_layout import FlowLayout


class MainWindow(QWidget):
    win_instance = None

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
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
        for _ in range(10):
            self.main_layout.addWidget(QPushButton("Hello"))

    def init_signals(self):
        pass
