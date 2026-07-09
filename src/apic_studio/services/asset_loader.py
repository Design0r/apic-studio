from __future__ import annotations

import shutil
from pathlib import Path
from queue import Queue
from typing import Callable, Optional

from PySide6.QtCore import QObject, QRunnable, Qt, QThread, QThreadPool, Signal
from PySide6.QtGui import QIcon

from apic_studio.core import Asset, img, settings
from apic_studio.core.settings import SettingsManager
from shared.logger import Logger


class AssetLoaderWorker(QObject):
    asset_loaded = Signal(object)
    pool_scanned = Signal(object, object)  # (pool: Path, assets: list[Path])
    _default_icon_cache: Optional[QIcon] = None

    def __init__(self, app_settings: SettingsManager, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._cache: dict[Path, Asset] = {}
        self._settings = app_settings

        # Each task is a (kind, path) pair: "load" a single asset, "scan" a
        # pool directory, or "stop" the run loop.
        self.task_queue: Queue[tuple[str, Path]] = Queue()
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
        self.task_queue.put(("load", path))

    def scan_pool(self, path: Path) -> None:
        self.task_queue.put(("scan", path))

    def stop(self) -> None:
        self._running = False
        self.task_queue.put(("stop", Path()))

    def run(self) -> None:
        while self._running:
            kind, path = self.task_queue.get()

            if kind == "stop":
                break

            if kind == "scan":
                self.pool_scanned.emit(path, self._scan_pool(path))
                continue

            asset = self.load_asset(path)
            if asset:
                self.asset_loaded.emit(asset)

    def _scan_pool(self, path: Path) -> list[Path]:
        if not path.exists() or not path.is_dir():
            return []

        return [
            x
            for x in sorted(path.iterdir(), key=lambda p: p.stem.lower())
            if self.is_asset(x)
        ]

    def _get_default_icon(self) -> QIcon:
        if AssetLoaderWorker._default_icon_cache is None:
            AssetLoaderWorker._default_icon_cache = self._create_icon(
                self._default_icon
            )
        return AssetLoaderWorker._default_icon_cache

    def load_asset(self, path: Path) -> Optional[Asset]:
        if cached := self._cache.get(path):
            return cached

        model, thumb = self._scan_asset(path)
        if not model:
            return None

        if thumb == self._default_icon and model.suffix.lower() in {".hdr", ".exr"}:
            thumb = self._create_thumbnail(model)

        if thumb == self._default_icon and model.suffix.lower() in {".jpg", ".png"}:
            thumb = self._create_sdr_thumbnail(model)

        icon = (
            self._get_default_icon()
            if thumb == self._default_icon
            else self._create_icon(thumb)
        )

        # Logger.debug(f"loaded asset from {model}")
        asset = Asset(model, icon, Path(thumb))
        self._cache[path] = asset

        return asset

    def _scan_asset(self, path: Path) -> tuple[Optional[Path], str]:
        if not path.is_dir():
            if path.suffix.lower() in Asset.ASSET_EXT:
                return path, self._default_icon
            return None, self._default_icon

        model: Optional[Path] = None
        thumb = self._default_icon

        asset_name = path.stem
        thumb_name = f"{path.stem}-thumbnail"

        for ext in Asset.ASSET_EXT:
            asset_path = path / f"{asset_name}{ext}"

            if asset_path.exists():
                model = asset_path
                break

        for ext in Asset.IMG_EXT:
            thumb_path = path / f"{thumb_name}{ext}"
            if thumb_path.exists():
                thumb = str(thumb_path)
                break

        # if thumb == self._default_icon:
        #     for ext in Asset.IMG_EXT:
        #         thumb_path = path / f"{asset_name}{ext}"
        #         if thumb_path.exists():
        #             thumb = str(thumb_path)
        #             break

        return model, thumb

    def _create_icon(self, thumbnail: str, size: int = 185) -> QIcon:
        icon = QIcon(thumbnail)

        available_sizes = icon.availableSizes()
        if available_sizes and available_sizes[0].width() != size:
            pixmap = icon.pixmap(available_sizes[0])
            scaled_pixmap = pixmap.scaled(
                size,
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation,
            )
            icon = QIcon(scaled_pixmap)

        return icon

    def _search_thumbnail(self, path: Path) -> str:
        if not path.is_dir():
            return self._default_icon

        for p in path.iterdir():
            if p.suffix.lower() in Asset.IMG_EXT:
                # Logger.debug(f"found thumbnail: {path / p.name}")
                return str(p)

        return self._default_icon

    def _search_3d_model(self, path: Path) -> Optional[Path]:
        is_dir = path.is_dir()
        if not is_dir and path.suffix.lower() in Asset.ASSET_EXT:
            return path

        if not is_dir:
            return None

        for p in path.iterdir():
            if p.suffix.lower() in Asset.ASSET_EXT:
                return p

        return None

    def _create_thumbnail(self, path: Path) -> str:
        size = self._settings.MaterialSettings.render_res_x
        thumb_path = path.parent / f"{path.stem}-thumbnail.jpg"
        try:
            img.create_sdr_preview(path, thumb_path, size)
            if thumb_path.exists():
                return str(thumb_path)
        except Exception as e:
            Logger.exception(e)
        return self._default_icon

    def _create_sdr_thumbnail(self, path: Path) -> str:
        size = self._settings.MaterialSettings.render_res_x
        thumb_path = path.parent / f"{path.stem}-thumbnail.jpg"
        try:
            img.downscale_sdr_image(path, thumb_path, size)
            if thumb_path.exists():
                return str(thumb_path)
        except Exception as e:
            Logger.exception(e)
        return self._default_icon

    def is_asset(self, path: Path) -> bool:
        if path in self._cache:
            return True
        return self._search_3d_model(path) is not None


class AssetLoader(QObject):
    asset_loaded = Signal(Asset)
    pool_scanned = Signal(object, object)  # (pool: Path, assets: list[Path])

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.worker = AssetLoaderWorker(settings.SettingsManager())
        self.t = QThread()

        self.worker.moveToThread(self.t)
        self.t.started.connect(self.worker.run)
        self.worker.asset_loaded.connect(self.on_asset_loaded)
        self.worker.pool_scanned.connect(self.on_pool_scanned)
        self.t.start()

    def get_asset(self, path: Path) -> Optional[Asset]:
        return self.worker.get_asset(path)

    def scan_pool(self, path: Path) -> None:
        self.worker.scan_pool(path)

    def load_asset(self, path: Path, refresh: bool = False):
        if refresh:
            self.worker.remove_from_cache(path)
        self.worker.add_task(path)

    def rename_asset(self, path: Path, name: str) -> Optional[Asset]:
        asset = self.worker.get_asset(path)
        if not asset:
            Logger.error(f"unable to rename, asset does not exist {path}")
            return

        asset = asset.rename(name, self.worker._create_icon)  # type: ignore
        return asset

    def on_asset_loaded(self, asset: Asset):
        self.asset_loaded.emit(asset)

    def on_pool_scanned(self, pool: Path, assets: list[Path]):
        self.pool_scanned.emit(pool, assets)

    def stop(self):
        self.worker.stop()
        self.t.quit()
        self.t.wait()


class CopyTask(QRunnable):
    def __init__(
        self, root: Path, files: list[str] | list[Path], notifier: AssetConverter
    ):
        super().__init__()
        self.root = root
        self.files = files
        self.notifier = notifier
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        self._running = True

        for i, f in enumerate(self.files):
            if not self._running:
                self.notifier.finished.emit()
                Logger.info("stopped copy task")
                return

            if isinstance(f, str):
                file = Path(f)
            else:
                file = f

            asset_dir = self.root / file.stem
            new_asset_path = asset_dir / file.name

            if asset_dir.exists():
                Logger.warning(f"asset directory already exists: {asset_dir}")
                self.notifier.progress.emit(i + 1)
                continue

            asset_dir.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(file, new_asset_path)
                self.notifier.progress.emit(i + 1)
            except Exception as e:
                Logger.exception(e)

        self.notifier.finished.emit()


class AssetConverter(QObject):
    progress = Signal(int)
    finished = Signal()

    def __init__(
        self, root_path: Optional[Path] = None, parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self.root = root_path
        self._pool = QThreadPool.globalInstance()
        self._running = True

    def set_root(self, path: Path):
        self.root = path

    def create_assets_from_files(
        self, files: list[str] | list[Path]
    ) -> Optional[CopyTask]:
        if not self.root:
            Logger.error("no root path set for asset converter")
            return

        task = CopyTask(self.root, files, self)
        self._pool.start(task)  # type: ignore
        return task

    @staticmethod
    def crawl_assets(
        root: Path,
        filter: Optional[Callable[[str], bool]] = None,
        suffix: str = ".c4d",
    ) -> dict[str, Path]:
        result: dict[str, Path] = {}

        for path, _, files in root.walk():
            for file in files:
                if (filter and not filter(file)) or not file.endswith(suffix):
                    continue

                result[file] = path / file

        return result
