from __future__ import annotations

from collections import deque
from functools import partial
from pathlib import Path
from typing import Deque, Optional

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QHBoxLayout, QMenu, QScrollArea, QWidget

from apic_studio.core import Asset
from apic_studio.core.settings import SettingsManager
from apic_studio.services import AssetLoader, BackupManager, DCCBridge, Screenshot
from apic_studio.ui.buttons import ViewportButton
from apic_studio.ui.dialogs import CreateBackupDialog, RenameAssetDialog
from apic_studio.ui.flow_layout import FlowLayout
from shared.logger import Logger


class Viewport(QWidget):
    asset_clicked = Signal(Asset)

    def __init__(
        self,
        dcc: DCCBridge,
        settings: SettingsManager,
        loader: AssetLoader,
        screenshot: Screenshot,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.loader = loader
        self.settings = settings
        self.screenshot = screenshot
        self.dcc = dcc
        self._widgets: dict[str, dict[str, ViewportButton]] = {
            "models": {},
            "apic_models": {},
            "materials": {},
            "hdris": {},
            "lightsets": {},
        }
        self.curr_view = "materials"
        self.curr_pool: Path
        self.backup = BackupManager()

        self._pending_assets: Deque[Path] = deque()
        self._load_timer: Optional[QTimer] = None
        self._batch_size: int = 25

        self.init_widgets()
        self.init_layouts()
        self.init_signals()

    def init_widgets(self):
        self.grid_widget = QWidget()
        self.scroll_area = QScrollArea()
        self.scroll_area.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self.scroll_area.setWidget(self.grid_widget)

    def init_layouts(self):
        self.flow_layout = FlowLayout(self.grid_widget)

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(5, 5, 0, 0)
        self.main_layout.addWidget(self.scroll_area)

    def init_signals(self):
        self.loader.asset_loaded.connect(self.on_asset_load)

        def load(x: Path):
            self.loader.load_asset(x, refresh=True)

        self.screenshot.created.connect(load)

    @property
    def widgets(self) -> dict[str, ViewportButton]:
        return self._widgets[self.curr_view]

    def on_asset_load(self, asset: Asset):
        w = self.widgets.get(asset.path.stem)
        if not w:
            Logger.error(f"Failed to find widget by asset name: {asset.path.stem}")
            return

        w.set_thumbnail(asset.icon, 185)
        w.set_file(asset.file, asset.size, asset.suffix)

    def _clear_layout(self):
        while self.flow_layout.count():
            item = self.flow_layout.takeAt(0)
            if not item:
                continue
            item.widget().setParent(None)

    def _start_incremental_load(self, force: bool) -> None:
        if self._load_timer and self._load_timer.isActive():
            self._load_timer.stop()

        self._load_timer = QTimer(self)
        self._load_timer.setInterval(0)
        self._load_timer.timeout.connect(lambda: self._process_batch(force))
        self._load_timer.start()

    def _process_batch(self, force: bool) -> None:
        for _ in range(self._batch_size):
            if not self._pending_assets:
                if self._load_timer:
                    self._load_timer.stop()
                return

            x = self._pending_assets.popleft()
            if not force and (cached_widget := self.widgets.get(x.stem)):
                self.flow_layout.addWidget(cached_widget)
                continue

            b = ViewportButton(x, (200, 200))
            b.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            b.customContextMenuRequested.connect(partial(self.on_context_menu, b))
            b.clicked.connect(partial(self.on_btn_click, x))

            self.widgets[x.stem] = b
            self.flow_layout.addWidget(b)
            self.loader.load_asset(x, refresh=force)

    def draw(
        self, path: Path, force: bool = False, filter: Optional[str] = None
    ) -> None:
        self._clear_layout()

        Logger.debug(f"drawing called: {path}")
        if not path or not path.exists():
            return

        self.curr_pool = path.parent
        self._pending_assets.clear()

        for x in sorted(path.iterdir(), key=lambda x: x.stem):
            if filter and filter.lower() not in x.stem.lower():
                continue

            if not self.loader.is_asset(x):
                continue

            self._pending_assets.append(x)

        if self._pending_assets:
            self._start_incremental_load(force)

    def on_btn_click(self, x: Path):
        asset = self.loader.get_asset(x)
        if asset:
            self.asset_clicked.emit(asset)

    def set_current_view(self, view: str):
        if view not in self._widgets:
            return

        self.curr_view = view
        self._clear_layout()

    def on_context_menu(self, btn: ViewportButton, point: QPoint):
        open_act = QAction("Open")
        open_act.triggered.connect(lambda: self.on_open_dialog(btn.file))

        import_act = QAction("Import")
        import_as_area = QAction("Import as Arealight")
        import_as_area.triggered.connect(lambda: self.dcc.hdri_import_as_area(btn.file))

        backup_act = QAction("Create Backup")
        backup_act.triggered.connect(lambda: self.on_backup(btn.file))

        repath_act = QAction("Repath Textures")
        repath_act.triggered.connect(lambda: self.dcc.repath_textures(btn.file))

        if self.curr_view in ("models", "apic_models", "lightsets"):
            import_act.triggered.connect(lambda: self.dcc.models_import(btn.file))
        elif self.curr_view == "materials":
            import_act.triggered.connect(lambda: self.dcc.materials_import(btn.file))
        elif self.curr_view == "hdris":
            import_act.setText("Import as Domelight")
            import_act.triggered.connect(lambda: self.dcc.hdri_import_as_dome(btn.file))

        render_act = QAction("Render Preview")
        render_act.triggered.connect(lambda: self.on_render(btn))

        delete_preview_act = QAction("Delete Preview")
        delete_preview_act.triggered.connect(lambda: self.on_del_preview(btn))

        screenshot_act = QAction("Create Screenshot")
        screenshot_act.triggered.connect(lambda: self.screenshot.show_dialog(btn.file))

        rename_act = QAction("Rename")
        rename_act.triggered.connect(lambda: self.rename_asset(btn))

        delete_act = QAction("Delete")
        delete_act.triggered.connect(lambda: self.delete_widget(btn))

        menu = QMenu()

        if self.curr_view not in ("hdris", "utils"):
            menu.addAction(open_act)

        menu.addAction(import_act)

        if self.curr_view == "hdris":
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

        menu.exec_(btn.mapToGlobal(point))

    def on_render(self, btn: ViewportButton):
        self.dcc.materials_preview_create(
            btn.file,
            callback=lambda: self.loader.load_asset(btn.file.parent, refresh=True),
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

    def on_del_preview(self, btn: ViewportButton):
        file_dir = btn.file.parent
        for f in file_dir.iterdir():
            if f.suffix.lower() not in Asset.IMG_EXT:
                continue
            Logger.debug(f"Deleting preview: {f}")
            f.unlink()
        self.loader.load_asset(file_dir, refresh=True)

    def delete_widget(self, btn: ViewportButton):
        del self.widgets[btn.file.stem]
        btn.setParent(None)
        btn.deleteLater()

    def shutdown(self):
        if self._load_timer:
            self._load_timer.stop()
            self._load_timer.deleteLater()

    def rename_asset(self, btn: ViewportButton):
        dialog = RenameAssetDialog(btn.file.stem)
        dialog.asset_renamed.connect(lambda x: self.on_rename_asset(btn, x))  # type: ignore
        dialog.exec()

    def on_rename_asset(self, btn: ViewportButton, name: str):
        if not name or not btn.file.exists():
            return

        new_asset = self.loader.rename_asset(btn.file.parent, name)
        if not new_asset:
            return

        self.dcc.repath_textures(new_asset.file)

        self.backup.rename_from_asset(new_asset.path, name)

        old_btn_key = btn.file.stem
        del self.widgets[old_btn_key]
        self.widgets[name] = btn

        self.loader.load_asset(new_asset.path)
