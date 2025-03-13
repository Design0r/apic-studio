__version__ = "0.1.1"
import sys

from PySide6.QtWidgets import QApplication

from apic_studio.core import db
from apic_studio.core.logger import Logger
from apic_studio.core.settings import SettingsManager  # noqa: F401
from apic_studio.resource import resources  # noqa: F401
from apic_studio.ui.main_window import MainWindow


class Application:
    def __init__(self) -> None:
        self.settings = SettingsManager()
        self.qapp = QApplication(sys.argv)
        self.window = MainWindow.show_window(self.settings)

        self.init()

    def init(self):
        self.settings.load_settings()
        db.init_db()

        self.qapp.setStyle("Fusion")

        Logger.write_to_file(self.settings.LOGGING_PATH)
        Logger.set_propagate(False)
        Logger.info("initializing Apic Studio...")

    def shutdown(self):
        Logger.info("shutting down Apic Studio...")

    def run(self):
        Logger.info("starting Apic Studio...")
        self.qapp.exec()
        self.shutdown()
