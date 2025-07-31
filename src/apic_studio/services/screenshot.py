import time
from pathlib import Path

import mss
from PIL import Image
from PySide6.QtCore import QCoreApplication, QObject, QPoint, Signal
from PySide6.QtGui import QGuiApplication

from apic_studio.ui.dialogs import ScreenshotDialog, ScreenshotResult
from shared.logger import Logger


class Screenshot(QObject):
    created = Signal(Path)

    def __init__(self) -> None:
        super().__init__()

    def show_dialog(self, path: Path):
        self.screenshot_frame = ScreenshotDialog(path)
        self.screenshot_frame.accepted.connect(self.on_accepted)
        self.screenshot_frame.exec_()

    def on_accepted(self, data: ScreenshotResult):
        self.screenshot_frame.setVisible(False)
        QCoreApplication.processEvents()
        time.sleep(0.2)

        screen_path = Path(data.folder, f"{data.asset_name}.jpg")
        self.create(screen_path, data.geometry)
        self.created.emit(data.folder)

    def create(self, path: Path, geometry: tuple[int, int, int, int]) -> None:
        x, y, w, h = geometry

        screen = QGuiApplication.screenAt(QPoint(x, y))
        dpr = screen.devicePixelRatio() if screen else 1.0
        width = screen.availableSize().width() * dpr
        height = screen.availableSize().height() * dpr

        phys_x = int((x - width) * dpr + width) if x > width else int(x * dpr)
        phys_y = int((y - height) * dpr + height) if y > height else int(y * dpr)
        phys_w = int(w * dpr)
        phys_h = int(h * dpr)

        with mss.mss() as sct:
            monitor = {
                "top": phys_y,
                "left": phys_x,
                "width": phys_w,
                "height": phys_h,
            }

            print("Logical geometry:", geometry)
            print("Device pixel ratio:", dpr)
            print("Physical grab monitor:", monitor)
            print("Available monitors:", sct.monitors)

            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            img.resize((350, 350)).save(path, "JPEG")
            Logger.info(f"saved Screenshot in {path}")
