from __future__ import annotations

import shutil
from pathlib import Path
from queue import Empty, Queue
from typing import Optional

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QIcon

from apic_studio.core import Asset, img, settings
from shared.logger import Logger


class AssetLoaderWorker(QObject):
    asset_loaded = Signal(object)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._cache: dict[Path, Asset] = {}

        self.task_queue: Queue[Path] = Queue()
        self._running = True
        self._default_icon = ":icons/tabler-icon-photo.png"

    def remove_from_cache(self, path: Path):
        try:
            del self._cache[path]
        except KeyError:
            pass

    def get_asset(self, path: Path) -> Optional[Asset]:
        return self._cache.get(path)

    def add_task(self, path: Path) -> None:
        self.task_queue.put(path)

    def stop(self) -> None:
        self._running = False
        self.task_queue.put(Path())

    def run(self) -> None:
        while self._running:
            try:
                path = self.task_queue.get()
            except Empty:
                continue

            asset = self.load_asset(path)
            if asset:
                self.asset_loaded.emit(asset)

    def load_asset(self, path: Path) -> Optional[Asset]:
        if cached := self._cache.get(path):
            return cached

        thumb = self._search_thumbnail(path)

        model = self._search_3d_model(path)
        if not model:
            return

        if thumb == self._default_icon and model.suffix.lower() in {".hdr", ".exr"}:
            self._create_thumbnail(model)
            thumb = self._search_thumbnail(path)

        icon = self._create_icon(thumb)

        # Logger.debug(f"loaded asset from {model}")
        asset = Asset(model, icon, Path(thumb))
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
            if p.suffix.lower() in Asset.IMG_EXT:
                # Logger.debug(f"found thumbnail: {path / p.name}")
                return str(path / p.name)

        return self._default_icon

    def _search_3d_model(self, path: Path) -> Optional[Path]:
        if not path.is_dir() and path.suffix.lower() in Asset.CG_EXT:
            return path

        if not path.is_dir():
            return None

        for p in path.iterdir():
            if p.suffix.lower() in Asset.CG_EXT:
                return path / p.name

        return None

    def _create_thumbnail(self, path: Path) -> Optional[Path]:
        size = settings.SettingsManager().MaterialSettings.render_res_x
        img.create_sdr_preview(path, path.parent / f"{path.stem}.jpg", size)

    def is_asset(self, path: Path) -> bool:
        return self._search_3d_model(path) is not None


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
        return self.worker.is_asset(path)

    def get_asset(self, path: Path) -> Optional[Asset]:
        return self.worker.get_asset(path)

    def load_asset(self, path: Path, refresh: bool = False):
        if refresh:
            self.worker.remove_from_cache(path)
        self.worker.add_task(path)

    def on_asset_loaded(self, asset: Asset):
        self.asset_loaded.emit(asset)

    def stop(self):
        self.worker.stop()
        self.t.quit()
        self.t.wait()


class AssetConverter:
    def __init__(self, root_path: Path = Path()) -> None:
        self.root = root_path

    def set_root(self, path: Path):
        self.root = path

    def create_asset_from_file(self, file: Path) -> Path:
        asset_dir = self.root / file.stem
        new_asset_path = asset_dir / file.name
        if asset_dir.exists():
            Logger.warning(f"asset directory already exists: {asset_dir}")
            return new_asset_path

        asset_dir.mkdir()
        try:
            shutil.copy2(file, new_asset_path)
        except FileNotFoundError as e:
            Logger.exception(e)
            return Path()

        return new_asset_path


def crawl_assets(root: Path) -> dict[str, Path]:
    result: dict[str, Path] = {}

    for path, _, files in root.walk():
        for file in files:
            if "REF" not in file or not file.endswith(".c4d"):
                continue
            result[file] = path / file

    print(result)
    return result
