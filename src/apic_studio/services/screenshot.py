import time
from pathlib import Path

import mss
from PIL import Image
from PySide6.QtCore import QCoreApplication, QObject, Signal

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

        with mss.mss() as sct:
            monitor = {
                "top": y,
                "left": x,
                "width": w,
                "height": h,
            }

            sct_img = sct.grab(monitor)
            img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            img.resize((350, 350)).save(path, "JPEG")
            Logger.info(f"saved Screenshot in {path}")
