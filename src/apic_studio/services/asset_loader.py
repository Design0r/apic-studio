from __future__ import annotations

import os
import shutil
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from queue import LifoQueue
from threading import Event, Lock
from typing import Callable, Optional

from PySide6.QtCore import QObject, QRunnable, Qt, QThread, QThreadPool, Signal
from PySide6.QtGui import QImage, QImageReader

from apic_studio.core import Asset, img, settings
from apic_studio.core.settings import SettingsManager
from shared.logger import Logger

ICON_SIZE = 185

# decoded thumbnails kept around, roughly 135KB each at ICON_SIZE
CACHE_SIZE = 512


class AssetLoaderWorker(QObject):
    asset_loaded = Signal(object)
    pool_scanned = Signal(object, object)  # (pool: Path, assets: list[Path])
    _default_icon_cache: Optional[QImage] = None

    def __init__(self, app_settings: SettingsManager, parent: Optional[QObject] = None):
        super().__init__(parent)
        # keyed by asset folder, oldest first: the least recently used entries
        # fall off the front once CACHE_SIZE is reached
        self._cache: OrderedDict[Path, Asset] = OrderedDict()
        self._settings = app_settings

        # what the pool scan already resolved for an asset folder, so loading it
        # does not have to walk the directory a second time
        self._scans: dict[Path, tuple[Path, str]] = {}

        # the cache and the two tables below are reached from the executor
        # threads and from the GUI thread, so mutations go through the lock
        self._lock = Lock()
        self._inflight: dict[Path, Event] = {}
        self._invalidated: set[Path] = set()

        # Each task is a (kind, path, generation) triple: "load" a single
        # asset, "scan" a pool directory, or "stop" the run loop. Last in is
        # first out, so the tiles the user just scrolled to are served before
        # whatever was queued for the rows they have already passed.
        self.task_queue: LifoQueue[tuple[str, Path, int]] = LifoQueue()

        # bumped whenever the viewport moves on, see cancel_pending
        self._generation = 0
        self._running = True
        self._default_icon = ":icons/tabler-icon-photo.png"

    def remove_from_cache(self, path: Path):
        with self._lock:
            self._cache.pop(path, None)
            self._scans.pop(path, None)

            if path in self._inflight:
                # a decode is already running against the files this call just
                # invalidated, mark it so its result is dropped, not cached
                self._invalidated.add(path)

    def get_asset(self, path: Path) -> Optional[Asset]:
        with self._lock:
            return self._take(path)

    def _take(self, path: Path) -> Optional[Asset]:
        """Read through the cache, marking the entry as freshly used. Lock held."""
        asset = self._cache.get(path)
        if asset is not None:
            self._cache.move_to_end(path)

        return asset

    def asset_file(self, path: Path) -> Optional[Path]:
        """Name an asset's model file without decoding its thumbnail.

        A tile that has never scrolled into view has no Asset behind it, so
        anything acting on the file itself - rendering previews, the context
        menu - has to resolve it. The pool scan usually already has.
        """
        with self._lock:
            asset = self._cache.get(path)
            if asset is not None:
                return asset.file

            scan = self._scans.get(path)

        if scan is not None:
            return scan[0]

        return self._resolve_asset(path)[0]

    def _keep(self, path: Path, asset: Asset) -> None:
        """Cache an asset and drop whatever aged out to make room. Lock held."""
        self._cache[path] = asset
        self._cache.move_to_end(path)

        while len(self._cache) > CACHE_SIZE:
            self._cache.popitem(last=False)

    def add_task(self, path: Path) -> None:
        self.task_queue.put(("load", path, self._generation))

    def scan_pool(self, path: Path) -> None:
        self.task_queue.put(("scan", path, self._generation))

    def cancel_pending(self) -> None:
        """Give up on work queued for a pool the viewport has already left.

        The queued tasks are not removed - they are stamped with the generation
        that was current when they went in, and both the run loop and the
        decode drop anything stamped with an older one. A pool switch during a
        big load therefore costs a few dictionary comparisons rather than
        thousands of thumbnail decodes nobody is waiting for.
        """
        self._generation += 1

    def stop(self) -> None:
        self._running = False
        self.task_queue.put(("stop", Path(), self._generation))

    def run(self) -> None:
        # Decoding thumbnails is the bulk of a pool load and releases the GIL,
        # so fan the work out instead of handling one asset at a time.
        pool = ThreadPoolExecutor(
            max_workers=min(8, (os.cpu_count() or 4)),
            thread_name_prefix="asset-loader",
        )
        try:
            while self._running:
                kind, path, gen = self.task_queue.get()

                if kind == "stop":
                    break

                if gen != self._generation:
                    continue

                if kind == "scan":
                    self.pool_scanned.emit(path, self._scan_pool(path))
                    continue

                pool.submit(self._load_and_emit, path, gen)
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

    def _load_and_emit(self, path: Path, gen: int = 0) -> None:
        if gen != self._generation:
            # queued for a pool that is no longer on screen, decoding it would
            # only push work in front of the tiles the user is looking at
            return

        # BaseException, not Exception: a panic raised by the Rust thumbnailer
        # derives straight from BaseException and would otherwise vanish into
        # the future's result and take this asset down silently.
        try:
            if asset := self.load_asset(path):
                self.asset_loaded.emit(asset)
        except BaseException as e:
            Logger.exception(e)  # type: ignore[arg-type]

    def _scan_pool(self, path: Path) -> list[Path]:
        if not path.is_dir():
            return []

        try:
            entries = list(os.scandir(path))
        except OSError as e:
            Logger.exception(e)
            return []

        found: list[Path] = []
        for entry in entries:
            child = Path(entry.path)

            if not entry.is_dir():
                if child.suffix.lower() in Asset.ASSET_EXT:
                    found.append(child)
                continue

            model, thumb = self._resolve_asset(child)
            if model is None:
                continue

            # hand the resolved paths to the load, it needs no further I/O
            self._scans[child] = (model, thumb)
            found.append(child)

        found.sort(key=lambda p: p.stem.lower())

        return found

    def _get_default_icon(self) -> QImage:
        if AssetLoaderWorker._default_icon_cache is None:
            AssetLoaderWorker._default_icon_cache = self._create_icon(
                self._default_icon
            )
        return AssetLoaderWorker._default_icon_cache

    def load_asset(self, path: Path) -> Optional[Asset]:
        while True:
            with self._lock:
                if cached := self._take(path):
                    return cached

                event = self._inflight.get(path)
                if event is None:
                    # nobody else holds this path, the decode is ours
                    self._inflight[path] = Event()
                    break

            # another thread is already decoding it, take its result instead of
            # reading and decoding the very same files a second time
            event.wait()

        return self._decode_asset(path)

    def _decode_asset(self, path: Path) -> Optional[Asset]:
        asset: Optional[Asset] = None
        try:
            asset = self._build_asset(path)
        finally:
            with self._lock:
                event = self._inflight.pop(path, None)

                if path in self._invalidated:
                    # a refresh landed mid-decode, what we just read is stale
                    self._invalidated.discard(path)
                    asset = None
                elif asset is not None:
                    self._keep(path, asset)

            if event is not None:
                event.set()

        return asset

    def _build_asset(self, path: Path) -> Optional[Asset]:
        scan = self._scans.pop(path, None)
        if scan is None:
            scan = self._resolve_asset(path)

        model, thumb = scan
        if not model:
            return None

        is_default_icon = thumb == self._default_icon

        if is_default_icon:
            s = model.suffix.lower()
            if s in Asset.HDR_IMG_EXT:
                thumb = self._create_thumbnail(model)
            elif s in Asset.SDR_IMG_EXT:
                thumb = self._create_sdr_thumbnail(model)

            # the generators fall back to the default icon on failure, so ask
            # again: a thumbnail that was just built is the one to show
            is_default_icon = thumb == self._default_icon

        icon = self._get_default_icon() if is_default_icon else self._create_icon(thumb)

        return Asset(model, icon, Path(thumb))

    def _resolve_asset(self, path: Path) -> tuple[Optional[Path], str]:
        """Find an asset folder's model file and thumbnail in one directory read.

        Both names follow from the folder name, so a single scandir replaces the
        exists() probe per extension: one round trip per asset instead of the
        four (a .c4d) to twelve (an .exr) it used to take, which is what
        scanning a pool on a network library spends all its time on.
        """
        try:
            names = {entry.name for entry in os.scandir(path)}
        except OSError:
            return None, self._default_icon

        model: Optional[Path] = None
        for ext in Asset.ASSET_EXT:
            name = f"{path.name}{ext}"
            if name in names:
                model = path / name
                break
        else:
            # the file may have drifted from its folder name, take any match
            for name in sorted(names):
                if os.path.splitext(name)[1].lower() in Asset.ASSET_EXT:
                    model = path / name
                    break

        thumb = self._default_icon
        for ext in Asset.SDR_IMG_EXT:
            name = f"{path.name}-thumbnail{ext}"
            if name in names:
                thumb = str(path / name)
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

        # match the paint device up front, otherwise drawImage converts the
        # format again on every repaint of the tile
        target = (
            QImage.Format.Format_ARGB32_Premultiplied
            if image.hasAlphaChannel()
            else QImage.Format.Format_RGB32
        )

        return image.convertToFormat(target)

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

    def cancel_pending(self) -> None:
        self.worker.cancel_pending()

    def asset_file(self, path: Path) -> Optional[Path]:
        return self.worker.asset_file(path)

    def load_now(self, path: Path) -> Optional[Asset]:
        """Decode on the calling thread. For the one asset a click needs."""
        return self.worker.load_asset(path)

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
