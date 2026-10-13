import logging
import sys
from pathlib import Path
from threading import Thread

from PySide6.QtWidgets import QApplication

from apic_studio.core import db
from apic_studio.core.settings import SettingsManager
from apic_studio.services import DCCBridge, PingService
from apic_studio.ui.main_window import MainWindow
from shared.logger import Logger


class Application:
    def __init__(self) -> None:
        self.settings = SettingsManager()
        self.app = QApplication(sys.argv)
        self.dcc = DCCBridge.create(timeout=5)
        self.window: MainWindow

    def init(self):
        self.settings.load_settings()

        Logger.write_to_file(
            Path(self.settings.CoreSettings._logging_path), level=logging.INFO
        )
        Logger.set_propagate(False)
        Logger.info("initializing Apic Studio...")

        db.init_db()

        self.app.setStyle("Fusion")
        self.window = MainWindow(self.dcc, self.settings)

    def shutdown(self):
        Logger.info("shutting down Apic Studio...")
        self.settings.save_settings()

        for bridge in self.dcc:
            try:
                bridge.close()
            except ConnectionRefusedError as e:
                Logger.exception(e)

        self.app.exit()

    def run(self):
        Logger.info("starting Apic Studio...")

        for bridge in self.dcc:
            Thread(target=bridge.connect, daemon=True).start()
            PingService(bridge.ctx)

        self.window.show()
        self.app.exec()
