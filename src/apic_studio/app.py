import logging
import sys

from PySide6.QtWidgets import QApplication

from apic_studio.core import db
from apic_studio.core.settings import SettingsManager
from apic_studio.ui.main_window import MainWindow
from shared.logger import Logger
from shared.network import Connection


class Application:
    def __init__(self) -> None:
        self.settings = SettingsManager()
        self.app = QApplication(sys.argv)
        self.connection = Connection.client_connection()

        self.init()

    def init(self):
        self.settings.load_settings()

        Logger.write_to_file(self.settings.LOGGING_PATH, level=logging.DEBUG)
        Logger.set_propagate(False)
        Logger.info("initializing Apic Studio...")

        db.init_db()

        self.app.setStyle("Fusion")
        self.window = MainWindow(self.connection, self.settings)

    def shutdown(self):
        Logger.info("shutting down Apic Studio...")
        self.settings.save_settings()

        try:
            self.connection.close()
        except ConnectionRefusedError as e:
            Logger.exception(e)

        self.app.exit()

    def run(self):
        Logger.info("starting Apic Studio...")

        self.connection.connect(self.settings.WindowSettings.address)
        self.window.show()
        self.app.exec()

        self.shutdown()
