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
from shared.network import Connection


class Application:
    def __init__(self) -> None:
        self.settings = SettingsManager()
        self.app = QApplication(sys.argv)
        self.connection = Connection.client_connection(
            timeout=5, name="cinema 4d connector"
        )
        self.dcc = DCCBridge(self.connection)
        self.nuke_connection = Connection.client_connection(
            timeout=5, name="nuke connector"
        )
        self.nuke = DCCBridge(self.nuke_connection)
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
        self.window = MainWindow(self.dcc, self.nuke, self.settings)

    def shutdown(self):
        Logger.info("shutting down Apic Studio...")
        self.settings.save_settings()

        for conn in (self.connection, self.nuke_connection):
            try:
                conn.close()
            except ConnectionRefusedError as e:
                Logger.exception(e)

        self.app.exit()

    def run(self):
        Logger.info("starting Apic Studio...")

        core = self.settings.CoreSettings
        for conn, address in (
            (self.connection, core.address),
            (self.nuke_connection, core.nuke_address),
        ):
            Thread(target=conn.connect, args=(address,), daemon=True).start()
            PingService(conn)

        self.window.show()
        self.app.exec()
