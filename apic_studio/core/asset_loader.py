from __future__ import annotations

from pathlib import Path
from queue import Empty, Queue
from typing import Optional

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QIcon


class Asset:
    def __init__(self, path: Path, icon: QIcon) -> None:
        self.path = path
        self.name = path.stem
        self.suffix = path.suffix
        self.size = path.stat().st_size
        self.icon = icon


class AssetLoaderWorker(QObject):
    asset_loaded = Signal(object)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._cache: dict[Path, Asset] = {}

        self.task_queue: Queue[Path] = Queue()
        self._running = True

    def add_task(self, path: Path) -> None:
        self.task_queue.put(path)

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        while self._running:
            try:
                path = self.task_queue.get()
            except Empty:
                continue

            asset = self.load_asset(path)
            self.asset_loaded.emit(asset)

    def load_asset(self, path: Path) -> Asset:
        if path in self._cache:
            return self._cache[path]

        width, height = 200, 200
        # thumbnail = str(path / path.stem / ".jpg")
        icon = QIcon(str(path))
        available_sizes = icon.availableSizes()
        if available_sizes and available_sizes[0].width() != width:
            pixmap = icon.pixmap(available_sizes[0])
            scaled_pixmap = pixmap.scaled(
                width,
                height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation,
            )
            icon = QIcon(scaled_pixmap)

        asset = Asset(path, icon)
        self._cache[path] = asset

        return asset


class AssetLoader(QObject):
    asset_loaded = Signal(Asset)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.worker = AssetLoaderWorker()
        self.t = QThread()

        self.worker.moveToThread(self.t)
        self.t.started.connect(self.worker.run)
        self.worker.asset_loaded.connect(self.on_asset_loaded)
        self.t.start()

    def load_asset(self, path: Path):
        self.worker.add_task(path)

    def on_asset_loaded(self, asset: Asset):
        self.asset_loaded.emit(asset)

    def stop(self):
        self.worker.stop()
        self.t.quit()
        self.t.wait()
