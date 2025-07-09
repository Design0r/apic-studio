import logging
import os
import sys

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from apic_studio.core import db
from apic_studio.core.settings import SettingsManager
from apic_studio.services import DCCBridge
from apic_studio.ui.main_window import MainWindow
from shared.logger import Logger
from shared.network import Connection

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
QCoreApplication.setAttribute(
    Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True
)  # scale UI to match DPI :contentReference[oaicite:0]{index=0}
QCoreApplication.setAttribute(
    Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True
)  # load @2x icons when available

# 2) Don’t let Qt round 1.5 up to 2.0 — pass it straight through:
#    must be called before creating the QGuiApplication/QApplication instance
QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
    Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
)
if sys.platform == "win32":
    import ctypes

    ctypes.windll.shcore.SetProcessDpiAwareness(2)


class Application:
    def __init__(self) -> None:
        self.settings = SettingsManager()
        self.app = QApplication(sys.argv)
        self.connection = Connection.client_connection()
        self.dcc = DCCBridge(self.connection)
        self.window: MainWindow

        self.init()

    def init(self):
        self.settings.load_settings()

        Logger.write_to_file(self.settings.LOGGING_PATH, level=logging.DEBUG)
        Logger.set_propagate(False)
        Logger.info("initializing Apic Studio...")

        db.init_db()

        self.app.setStyle("Fusion")
        self.window = MainWindow(self.dcc, self.settings)

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

        self.connection.connect(self.settings.CoreSettings.address)
        self.window.show()
        self.app.exec()

        self.shutdown()
