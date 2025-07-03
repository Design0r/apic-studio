from __future__ import annotations

from pathlib import Path
from queue import Empty, Queue
from typing import Optional

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QIcon

IMG_EXT = (".jpg", ".png")
CG_EXT = (".c4d",)


class Asset:
    __slots__ = ("path", "name", "suffix", "size", "icon", "file")

    def __init__(self, file: Path, icon: QIcon) -> None:
        self.file = file
        self.path = file.parent
        self.name = file.stem
        self.size = file.stat().st_size
        self.icon = icon
        self.suffix = file.suffix

    def __repr__(self) -> str:
        return f"Asset(path={self.file}, icon={self.icon})"


class AssetLoaderWorker(QObject):
    asset_loaded = Signal(object)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._cache: dict[Path, Asset] = {}

        self.task_queue: Queue[Path] = Queue()
        self._running = True
        self._default_icon = ":icons/tabler-icon-photo.png"

    def add_task(self, path: Path) -> None:
        self.task_queue.put(path)

    def stop(self) -> None:
        self._running = False

    def run(self) -> None:
        while self._running:
            try:
                path = self.task_queue.get(timeout=0.2)
            except Empty:
                continue

            asset = self.load_asset(path)
            if asset:
                self.asset_loaded.emit(asset)

    def load_asset(self, path: Path) -> Optional[Asset]:
        if path in self._cache:
            return self._cache[path]

        icon = self._create_icon(self._search_thumbnail(path))
        model = self._search_3d_model(path)
        print(f"Loading asset from {model}...")
        if not model:
            return

        asset = Asset(model, icon)
        self._cache[path] = asset

        return asset

    def _create_icon(self, thumbnail: str) -> QIcon:
        width, height = 200, 200
        icon = QIcon(thumbnail)

        available_sizes = icon.availableSizes()
        if available_sizes and available_sizes[0].width() != width:
            pixmap = icon.pixmap(available_sizes[0])
            scaled_pixmap = pixmap.scaled(
                width,
                height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            icon = QIcon(scaled_pixmap)

        return icon

    def _search_thumbnail(self, path: Path) -> str:
        if not path.is_dir():
            return self._default_icon

        for p in path.iterdir():
            if p.suffix.lower() in IMG_EXT:
                return str(path / p.name)

        return self._default_icon

    def _search_3d_model(self, path: Path) -> Optional[Path]:
        if not path.is_dir() and path.suffix.lower() in CG_EXT:
            return path

        if not path.is_dir():
            return None

        for p in path.iterdir():
            print(p)
            if p.suffix.lower() in CG_EXT:
                return path / p.name

        return None


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

    def is_asset(self, path: Path) -> bool:
        if path.is_dir():
            return True

        return path.suffix in CG_EXT

    def load_asset(self, path: Path):
        self.worker.add_task(path)

    def on_asset_loaded(self, asset: Asset):
        self.asset_loaded.emit(asset)

    def stop(self):
        self.worker.stop()
        self.t.quit()
        self.t.wait()
