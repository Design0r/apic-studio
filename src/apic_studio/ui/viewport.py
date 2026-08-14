from __future__ import annotations

import shutil
import time
from pathlib import Path

from PySide6.QtCore import QPoint, QSize, QSortFilterProxyModel, Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QListView,
    QMenu,
    QWidget,
)

from apic_studio.core import Asset
from apic_studio.core.settings import SettingsManager
from apic_studio.services import AssetLoader, BackupManager, DCCBridge, Screenshot
from apic_studio.ui.asset_view import (
    KEY_ROLE,
    AssetDelegate,
    AssetModel,
    AssetRow,
)
from apic_studio.ui.dialogs import (
    CreateBackupDialog,
    DeleteAssetDialog,
    RenameAssetDialog,
)
from shared.logger import Logger

VIEWS = ("textures", "models", "apic_models", "materials", "hdris", "lightsets")

VIEW_STYLE = """
QListView {
    background-color: rgb(68,68,68);
    border: none;
}
"""


class AssetListView(QListView):
    """Icon-mode list with a wheel tick that moves less than a row of tiles.

    QListView re-pins the vertical single step to a full item height on every
    geometry update, so the step has to be restored after each one.
    """

    SCROLL_STEP = 40

    def updateGeometries(self) -> None:
        super().updateGeometries()
        self.verticalScrollBar().setSingleStep(self.SCROLL_STEP)


class Viewport(QWidget):
    asset_clicked = Signal(Asset)

    def __init__(
        self,
        dcc: DCCBridge,
        settings: SettingsManager,
        loader: AssetLoader,
        screenshot: Screenshot,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.loader = loader
        self.settings = settings
        self.screenshot = screenshot
        self.dcc = dcc

        # one model per view so switching views keeps each pool's contents
        self._models: dict[str, AssetModel] = {}
        self._proxies: dict[str, QSortFilterProxyModel] = {}
        for name in VIEWS:
            model = AssetModel(self)
            proxy = QSortFilterProxyModel(self)
            proxy.setSourceModel(model)
            proxy.setFilterRole(KEY_ROLE)
            proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
            self._models[name] = model
            self._proxies[name] = proxy

        self.curr_view = "materials"
        self.curr_pool: Path
        self.backup = BackupManager()

        self._pool_asset_index: dict[Path, list[Path]] = {}

        self._pending_pool: Path | None = None
        self._drawn_pool: Path | None = None
        self._draw_filter: str | None = None
        self._draw_force: bool = False
        self._draw_timer: float = 0.0

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

    def init_widgets(self):
        self.view = AssetListView()
        self.view.setModel(self.proxy)
        self.view.setItemDelegate(AssetDelegate(self.view))
        self.view.setViewMode(QListView.ViewMode.IconMode)
        self.view.setFlow(QListView.Flow.LeftToRight)
        self.view.setWrapping(True)
        self.view.setResizeMode(QListView.ResizeMode.Adjust)
        self.view.setMovement(QListView.Movement.Static)
        # only visible tiles are ever painted, so the pool size stops mattering
        self.view.setUniformItemSizes(True)
        self.view.setLayoutMode(QListView.LayoutMode.Batched)
        self.view.setBatchSize(128)
        self.view.setSpacing(3)
        self.view.setGridSize(QSize(206, 256))
        self.view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.setStyleSheet(VIEW_STYLE)
        # Fusion does not enable hover on item views the way the native Windows
        # styles do, so ask for the hover events the delegate paints with
        self.view.viewport().setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def init_layouts(self):
        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 0, 0)
        self.main_layout.addWidget(self.view)

    def init_signals(self):
        self.loader.asset_loaded.connect(self.on_asset_load)
        self.loader.pool_scanned.connect(self.on_pool_scanned)
        self.view.clicked.connect(self.on_item_clicked)
        self.view.customContextMenuRequested.connect(self.on_context_menu)

        def load(x: Path):
            self.loader.load_asset(x, refresh=True)

        self.screenshot.created.connect(load)

    @property
    def model(self) -> AssetModel:
        return self._models[self.curr_view]

    @property
    def proxy(self) -> QSortFilterProxyModel:
        return self._proxies[self.curr_view]

    def asset_files(self) -> list[Path]:
        return self.model.files()

    def on_asset_load(self, asset: Asset):
        for model in self._models.values():
            if model.update_asset(asset):
                break

    def clear(self) -> None:
        self._drawn_pool = None
        self.model.set_assets([])

    def draw(self, path: Path, force: bool = False, filter: str | None = None) -> None:
        self._draw_filter = filter.lower() if filter else None
        # filtering is a proxy pass over the model, no widgets are touched
        self.proxy.setFilterFixedString(self._draw_filter or "")

        if not force and path and path == self._drawn_pool:
            return

        self.clear()

        if not path or not path.exists():
            self._pending_pool = None
            return

        self.curr_pool = path.parent
        self._draw_force = force
        self._pending_pool = path

        cached = self._pool_asset_index.get(path)
        if cached and not force:
            self._render_assets(cached)
            return

        self.loader.scan_pool(path)
        Logger.info(f"loading pool {self.curr_pool.stem}...")
        self._draw_timer = time.perf_counter()

    def on_pool_scanned(self, path: Path, assets: list[Path]) -> None:
        self._pool_asset_index[path] = assets
        if path != self._pending_pool:
            return
        self._render_assets(assets)

    def _render_assets(self, assets: list[Path]) -> None:
        force = self._draw_force
        model = self.model

        model.set_assets(assets)
        self._drawn_pool = self._pending_pool

        for x in assets:
            cached = None if force else self.loader.get_asset(x)
            if cached is not None:
                # already decoded, no need to go through the loader thread
                model.update_asset(cached)
                continue

            self.loader.load_asset(x, refresh=force)

        if self._draw_timer:
            Logger.info(
                f"finished loading pool {self.curr_pool.stem} in "
                f"{(time.perf_counter() - self._draw_timer):.2f}s"
            )
            self._draw_timer = 0.0

    def _row_at(self, point: QPoint) -> AssetRow | None:
        index = self.view.indexAt(point)
        if not index.isValid():
            return None

        return self.model.row_at(self.proxy.mapToSource(index))

    def on_item_clicked(self, index) -> None:
        row = self.model.row_at(self.proxy.mapToSource(index))
        if not row:
            return

        asset = self.loader.get_asset(row.asset)
        if asset:
            self.asset_clicked.emit(asset)

    def set_current_view(self, view: str):
        if view not in self._models:
            return

        self.curr_view = view
        self._drawn_pool = None
        self.view.setModel(self.proxy)

    def on_context_menu(self, point: QPoint):
        row = self._row_at(point)
        if not row:
            return

        file = row.file

        open_act = QAction("Open")
        open_act.triggered.connect(lambda: self.on_open_dialog(file))

        import_act = QAction("Import")
        import_as_area = QAction("Import as Arealight")
        import_as_area.triggered.connect(lambda: self.dcc.hdri_import_as_area(file))

        reference_act = QAction("Reference")

        backup_act = QAction("Create Backup")
        backup_act.triggered.connect(lambda: self.on_backup(file))

        repath_act = QAction("Repath Textures")
        repath_act.triggered.connect(lambda: self.dcc.repath_textures(file))

        if self.curr_view in ("models", "apic_models", "lightsets"):
            import_act.triggered.connect(lambda: self.dcc.models_import(file))
            reference_act.triggered.connect(lambda: self.dcc.models_reference(file))
        elif self.curr_view == "materials":
            import_act.triggered.connect(lambda: self.dcc.materials_import(file))
        elif self.curr_view == "hdris":
            import_act.setText("Import as Domelight")
            import_act.triggered.connect(lambda: self.dcc.hdri_import_as_dome(file))

        render_act = QAction("Render Preview")
        render_act.triggered.connect(lambda: self.on_render(file))

        delete_preview_act = QAction("Delete Preview")
        delete_preview_act.triggered.connect(lambda: self.on_del_preview(file))

        screenshot_act = QAction("Create Screenshot")
        screenshot_act.triggered.connect(lambda: self.screenshot.show_dialog(file))

        rename_act = QAction("Rename")
        rename_act.triggered.connect(lambda: self.rename_asset(file))

        delete_act = QAction("Delete")
        delete_act.triggered.connect(lambda: self.on_del_asset(file))

        menu = QMenu()

        if self.curr_view not in ("hdris", "utils"):
            menu.addAction(open_act)

        if self.curr_view in ("models", "apic_models", "lightsets"):
            menu.addAction(reference_act)

        if self.curr_view != "textures":
            menu.addAction(import_act)

        if self.curr_view in ("hdris", "textures"):
            menu.addAction(import_as_area)
            menu.addAction(delete_preview_act)

        menu.addSeparator()

        if self.curr_view in ("models", "apic_models", "lightsets"):
            menu.addAction(screenshot_act)
            menu.addAction(delete_preview_act)
            menu.addAction(backup_act)
            menu.addAction(repath_act)

        if self.curr_view == "materials":
            menu.addAction(render_act)
            menu.addAction(delete_preview_act)
            menu.addAction(backup_act)
            menu.addAction(repath_act)

        menu.addSeparator()
        menu.addAction(rename_act)
        menu.addAction(delete_act)

        menu.exec_(self.view.viewport().mapToGlobal(point))

    def on_render(self, file: Path):
        self.dcc.materials_preview_create(
            file,
            callback=lambda: self.loader.load_asset(file.parent, refresh=True),
        )

    def on_backup(self, path: Path):
        self.backup.create(path)

    def on_open_dialog(self, path: Path):
        def on_backup_open(path: Path):
            self.backup.create(path)
            self.dcc.file_open(path)

        backup = CreateBackupDialog()
        backup.accepted.connect(lambda: on_backup_open(path))
        backup.rejected.connect(lambda: self.dcc.file_open(path))
        backup.exec()

    def on_del_preview(self, file: Path):
        file_dir = file.parent
        for f in file_dir.iterdir():
            if f.suffix.lower() not in Asset.SDR_IMG_EXT:
                continue
            if not f.stem.endswith("-thumbnail"):
                continue
            Logger.debug(f"Deleting preview: {f}")
            f.unlink()
        self.loader.load_asset(file_dir, refresh=True)

    def on_del_asset(self, file: Path):
        dialog = DeleteAssetDialog(file.stem)
        dialog.accepted.connect(lambda: self.delete_asset(file))
        dialog.exec()

    def delete_asset(self, file: Path):
        asset_dir = file if file.is_dir() else file.parent

        self.model.remove(asset_dir)
        self._forget(asset_dir)
        shutil.rmtree(asset_dir, ignore_errors=True)

        Logger.info(f"deleted asset {asset_dir.name}")

    def shutdown(self):
        pass

    def rename_asset(self, file: Path):
        dialog = RenameAssetDialog(file.stem)
        dialog.asset_renamed.connect(lambda x: self.on_rename_asset(file, x))  # type: ignore
        dialog.exec()

    def on_rename_asset(self, file: Path, name: str):
        if not name or not file.exists():
            return

        asset_dir = file.parent
        new_asset = self.loader.rename_asset(asset_dir, name)
        if not new_asset:
            return

        self.dcc.repath_textures(new_asset.file)

        self.backup.rename_from_asset(new_asset.path, name)

        self.model.rename(asset_dir, new_asset)
        self._forget(asset_dir, replacement=new_asset.path)

        self.loader.load_asset(new_asset.path)

    def _forget(self, asset_dir: Path, replacement: Path | None = None) -> None:
        """Drop a path the pool no longer holds, so a redraw cannot resurrect it."""
        self.loader.forget(asset_dir)

        for pool, assets in self._pool_asset_index.items():
            if asset_dir not in assets:
                continue

            if replacement:
                assets[assets.index(asset_dir)] = replacement
            else:
                assets.remove(asset_dir)

            self._pool_asset_index[pool] = assets
            break
