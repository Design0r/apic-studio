import time
from pathlib import Path

import rust_thumbnails
from PySide6.QtCore import QCoreApplication, QObject, QPoint, QTimer, Signal
from PySide6.QtGui import QGuiApplication

from apic_studio.core.settings import SettingsManager
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

        QTimer.singleShot(200, lambda: self._continue_screenshot(data))

    def _continue_screenshot(self, data: ScreenshotResult):
        screen_path = Path(data.folder, f"{data.asset_name}.png")
        self.create(screen_path, data.geometry)
        self.created.emit(data.folder)

    def create(self, path: Path, geometry: tuple[int, int, int, int]) -> None:
        x, y, w, h = geometry
        s = SettingsManager().MaterialSettings.render_res_x

        path = path.parent / f"{path.stem}-thumbnail{path.suffix}"

        screen = QGuiApplication.screenAt(QPoint(x, y))
        if not screen:
            screen = QGuiApplication.primaryScreen()

        dpr = screen.devicePixelRatio() if screen else 1.0

        # Qt hands out logical coordinates on the virtual desktop, the capture
        # backend wants physical ones. Scale the offset inside the screen the
        # region sits on, so screens left of / above the primary keep their
        # negative origin instead of wrapping around.
        origin = screen.geometry().topLeft() if screen else QPoint(0, 0)
        phys_x = int(origin.x() + (x - origin.x()) * dpr)
        phys_y = int(origin.y() + (y - origin.y()) * dpr)
        phys_w = int(w * dpr)
        phys_h = int(h * dpr)

        try:
            rust_thumbnails.screenshot(str(path), phys_x, phys_y, phys_w, phys_h, s)
        except Exception as e:
            Logger.exception(e)
            return

        Logger.info(f"saved screenshot to: {path}")
