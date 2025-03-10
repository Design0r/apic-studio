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


class AssetLoader:
    def __init__(self) -> None:
        self._cache: dict[Path, Asset] = {}

    def load_asset(self, path: Path) -> Asset:
        if path in self._cache:
            return self._cache[path]

        width, height = 200, 200
        # thumbnail = str(path / path.stem / ".jpg")
        icon = QIcon(str(path))
        available_sizes = icon.availableSizes()
        if available_sizes and available_sizes[0].width() < width:
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

    def load_dir(self, path: Path):
        pass


class AssetLoaderWorker(QObject):
    assetLoaded = Signal(object)

    def __init__(self, asset_loader: AssetLoader, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.asset_loader = asset_loader
        self.task_queue: Queue[Path] = Queue()
        self._running = True

    def add_task(self, path: Path) -> None:
        self.task_queue.put(path)

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        while self._running:
            try:
                path = self.task_queue.get(timeout=0.1)
            except Empty:
                continue

            asset = self.asset_loader.load_asset(path)
            self.assetLoaded.emit(asset)


class AsyncAssetLoader(QObject):
    asset_loaded = Signal(Asset)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.asset_loader = AssetLoader()
        self.worker = AssetLoaderWorker(self.asset_loader)
        self.t = QThread()

        self.worker.moveToThread(self.t)
        self.t.started.connect(self.worker.run)
        self.worker.assetLoaded.connect(self.on_asset_loaded)
        self.t.start()

    def load_asset_async(self, path: Path) -> None:
        self.worker.add_task(path)

    def on_asset_loaded(self, asset: Asset) -> None:
        self.asset_loaded.emit(asset)

    def stop(self) -> None:
        self.worker.stop()
        self.t.quit()
        self.t.wait()
