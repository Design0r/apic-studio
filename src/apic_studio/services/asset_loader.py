from __future__ import annotations

import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from queue import Queue
from typing import Callable, Optional

from PySide6.QtCore import QObject, QRunnable, Qt, QThread, QThreadPool, Signal
from PySide6.QtGui import QImage, QImageReader

from apic_studio.core import Asset, img, settings
from apic_studio.core.settings import SettingsManager
from shared.logger import Logger

ICON_SIZE = 185


class AssetLoaderWorker(QObject):
    asset_loaded = Signal(object)
    pool_scanned = Signal(object, object)  # (pool: Path, assets: list[Path])
    _default_icon_cache: Optional[QImage] = None

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
        # Decoding thumbnails is the bulk of a pool load and releases the GIL,
        # so fan the work out instead of handling one asset at a time.
        pool = ThreadPoolExecutor(
            max_workers=min(8, (os.cpu_count() or 4)),
            thread_name_prefix="asset-loader",
        )
        try:
            while self._running:
                kind, path = self.task_queue.get()

                if kind == "stop":
                    break

                if kind == "scan":
                    self.pool_scanned.emit(path, self._scan_pool(path))
                    continue

                pool.submit(self._load_and_emit, path)
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

    def _load_and_emit(self, path: Path) -> None:
        # BaseException, not Exception: a panic raised by the Rust thumbnailer
        # derives straight from BaseException and would otherwise vanish into
        # the future's result and take this asset down silently.
        try:
            if asset := self.load_asset(path):
                self.asset_loaded.emit(asset)
        except BaseException as e:
            Logger.exception(e)  # type: ignore[arg-type]

    def _scan_pool(self, path: Path) -> list[Path]:
        if not path.exists() or not path.is_dir():
            return []

        return [
            x
            for x in sorted(path.iterdir(), key=lambda p: p.stem.lower())
            if self.is_asset(x)
        ]

    def _get_default_icon(self) -> QImage:
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

        is_default_icon = thumb == self._default_icon

        if is_default_icon:
            s = model.suffix.lower()
            if s in Asset.HDR_IMG_EXT:
                thumb = self._create_thumbnail(model)
            elif s in Asset.SDR_IMG_EXT:
                thumb = self._create_sdr_thumbnail(model)

        icon = self._get_default_icon() if is_default_icon else self._create_icon(thumb)

        asset = Asset(model, icon, Path(thumb))
        self._cache[path] = asset

        return asset

    def _scan_asset(self, path: Path) -> tuple[Optional[Path], str]:
        model: Optional[Path] = None
        thumb = self._default_icon

        asset_name = path.name
        thumb_name = f"{path.name}-thumbnail"

        for ext in Asset.ASSET_EXT:
            asset_path = path / f"{asset_name}{ext}"

            if asset_path.exists():
                model = asset_path
                break

        for ext in Asset.SDR_IMG_EXT:
            thumb_path = path / f"{thumb_name}{ext}"
            if thumb_path.exists():
                thumb = str(thumb_path)
                break

        return model, thumb

    def _create_icon(self, thumbnail: str, size: int = ICON_SIZE) -> QImage:
        # QImage, not QIcon/QPixmap: pixmaps may only be touched on the GUI
        # thread, and asking the decoder for the reduced size up front beats
        # decoding at full resolution and scaling afterwards.
        reader = QImageReader(thumbnail)
        reader.setAutoTransform(True)

        source = reader.size()
        if source.isValid() and (source.width() > size or source.height() > size):
            reader.setScaledSize(
                source.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio)
            )

        image = reader.read()
        if image.isNull():
            Logger.warning(f"could not decode {thumbnail}: {reader.errorString()}")

        return image

    def _search_asset(self, path: Path) -> Optional[Path]:
        is_dir = path.is_dir()
        if not is_dir and path.suffix.lower() in Asset.ASSET_EXT:
            return path

        if not is_dir:
            return None

        # assets are named after their folder, so probing the expected names is
        # far cheaper than listing the directory
        for ext in Asset.ASSET_EXT:
            candidate = path / f"{path.name}{ext}"
            if candidate.exists():
                return candidate

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

        return self._search_asset(path) is not None


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

    def forget(self, path: Path) -> None:
        self.worker.remove_from_cache(path)

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
            except Exception as e:
                Logger.exception(e)

            # always advance, a stalled counter leaves the progress dialog open
            self.notifier.progress.emit(i + 1)

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
