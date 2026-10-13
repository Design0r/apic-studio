import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from apic_studio.core.settings import SettingsManager
from shared.logger import Logger
from shared.messaging import Message

from .base import BaseBridge, CmdBuilder, RenderThread


class Cinema4D:
    def __init__(self, install_location: Path | None = None) -> None:
        self.install_location = install_location
        self.default_locations = {
            "darwin": Path(""),
            "win32": Path("C:\\Program Files\\"),
        }
        self.platform = sys.platform
        self._renders: list[RenderThread] = []

    @property
    def default_location(self) -> Path:
        return self.default_locations[self.platform]

    def _get_base(self) -> Path:
        loc = self.install_location or self.default_location
        res = list(loc.glob("Maxon Cinema 4D*"))
        latest = res[-1]
        return latest

    def get_versions(self) -> list[Path]:
        loc = self.install_location or self.default_location
        return list(loc.glob("Maxon Cinema 4D*"))

    def _get_version_base(self, version: str) -> Path | None:
        versions = self.get_versions()
        if not versions:
            Logger.error(
                "no Cinema 4D version detected, install Cinema 4D or specify a custom installation location"
            )
            return
        for v in versions:
            if version in v.stem:
                return v

    def get_exe(self, version: str | None = None) -> Path | None:
        exe = "Cinema 4D.exe"
        if not version:
            return self._get_base() / exe

        if v := self._get_version_base(version):
            return v / exe

    def get_batch(self, version: str | None = None) -> Path | None:
        exe = "Commandline.exe"
        if not version:
            return self._get_base() / exe

        if v := self._get_version_base(version):
            return v / exe

    def get_py(self, version: str | None = None) -> Path | None:
        exe = "c4dpy.exe"
        if not version:
            return self._get_base() / exe

        if v := self._get_version_base(version):
            return v / exe

    def run_exe(self, args: list[str]) -> None:
        raise NotImplementedError()

    def run_py(self, args: list[str], callback: Callable[[], None] | None = None):
        cmd = f"{self.get_py()} {' '.join(args)}"
        rt = RenderThread(cmd)
        self._renders.append(rt)

        def on_finished():
            if callback:
                Logger.info("Finished c4dpy process")
                callback()
            if rt in self._renders:
                self._renders.remove(rt)
            rt.deleteLater()

        rt.finished.connect(on_finished)
        Logger.debug(f"Starting c4dpy with cmd: {cmd}")
        rt.start()

    def run_batch(self, args: list[str]):
        cmd = [str(self.get_batch()), *args]
        subprocess.run(cmd, check=False)

    def versions(self) -> list[Path]:
        loc = self.default_location
        return list(loc.glob("Maxon Cinema 4D*"))


class Cinema4DBridge(BaseBridge):
    key = "c4d"
    label = "Cinema 4D"
    short_label = "C4D"

    def address(self) -> tuple[str, int]:
        return SettingsManager().CoreSettings.address

    def models_export_selected(
        self, path: Path, globalize_textures: bool = False
    ) -> Message:
        res = self.call(
            "models.export.selected",
            {"path": str(path), "globalize_textures": globalize_textures},
        )
        if self.is_err(res):
            Logger.error(f"failed to export asset: {path.name} to {path}: {res}")
        return res

    def models_import(self, path: Path) -> Message:
        res = self.call("models.import", {"path": str(path)})
        if self.is_err(res):
            Logger.error(f"failed to import asset: {path.name} to {path}: {res}")

        return res

    def models_reference(self, path: Path) -> Message:
        res = self.call("models.reference", {"path": str(path)})
        if self.is_err(res):
            Logger.error(f"failed to reference asset: {path.name} to {path}: {res}")

        return res

    def save_as(self, path: Path, globalize_textures: bool = False) -> Message:
        res = self.call(
            "core.file.save_as",
            {"path": str(path), "globalize_textures": globalize_textures},
        )
        if self.is_err(res):
            Logger.error(f"failed to save as: {path.name} to {path}: {res}")

        return res

    def materials_list(self) -> Message:
        res = self.call("materials.list")
        if self.is_err(res):
            Logger.error(f"failed to list materials: {res}")

        return res

    def materials_export(
        self, materials: list[str], path: Path, globalize_tetxures: bool = False
    ) -> Message:
        res = self.call(
            "materials.export",
            data={
                "materials": materials,
                "path": str(path),
                "globalize_textures": globalize_tetxures,
            },
        )
        if self.is_err(res):
            Logger.error(f"failed to export materials: {res}")

        return res

    def materials_import(self, path: Path) -> Message:
        res = self.call("materials.import", {"path": str(path)})
        if self.is_err(res):
            Logger.error(f"failed to import asset: {path.name}: {res}")

        return res

    def materials_preview_create(
        self, path: Path, callback: Callable[[], None] | None = None
    ):
        render_material([path], callback=callback)

    def materials_preview_create_all(
        self, path: list[Path], callback: Callable[[], None] | None = None
    ):
        render_material(path, callback=callback)

    def hdri_import_as_dome(self, path: Path) -> Message:
        res = self.call("hdris.import.domelight", {"path": str(path)})
        if self.is_err(res):
            Logger.error(f"failed to import hdri: {path.name}: {res}")

        return res

    def hdri_import_as_area(self, path: Path) -> Message:
        res = self.call("hdris.import.arealight", {"path": str(path)})
        if self.is_err(res):
            Logger.error(f"failed to import hdri: {path.name}: {res}")

        return res

    def repath_textures(
        self,
        path: Path,
        callback: Callable[[], None] | None = None,
        nocopy: bool = False,
    ):
        repath_textures(path, callback=callback, nocopy=nocopy)

    def batch_repath_textures(
        self, paths: list[Path], callback: Callable[[], None] | None = None
    ):
        def _seq_repath():
            try:
                p = paths.pop()
            except IndexError:
                return

            if not p:
                return

            self.repath_textures(p, _seq_repath)
            if callback:
                callback()

        _seq_repath()

    def settings_export_all(self, path: Path) -> Message:
        res = self.call("core.settings.export.all", {"path": str(path)})
        if self.is_err(res):
            Logger.error(f"failed to open file: {path.name}: {res}")

        return res

    def settings_export_redshift(self, path: Path) -> Message:
        res = self.call("core.settings.export.redshift", {"path": str(path)})
        if self.is_err(res):
            Logger.error(f"failed to open file: {path.name}: {res}")

        return res

    def settings_export_c4d(self, path: Path) -> Message:
        res = self.call("core.settings.export.c4d", {"path": str(path)})
        if self.is_err(res):
            Logger.error(f"failed to open file: {path.name}: {res}")

        return res

    def settings_import(self, path: Path) -> Message:
        res = self.call("core.settings.import", {"path": str(path)})
        if self.is_err(res):
            Logger.error(f"failed to open file: {path.name}: {res}")

        return res


def render_material(materials: list[Path], callback: Callable[[], None] | None = None):
    builder = CmdBuilder()
    s = SettingsManager()
    m = s.MaterialSettings
    p = Path(s.CoreSettings.root_path) / "scripts" / "render_material.py"
    if not p.exists():
        p = (
            Path(s.CoreSettings.root_path)
            / "src"
            / "apic_studio"
            / "scripts"
            / "render_material.py"
        )

    builder.add_positional(str(p))

    builder.add_flag("--scene", Path(m.render_scene))
    builder.add_flag("--object", m.render_object)
    builder.add_flag("--camera", m.render_cam)
    builder.add_flag("--width", m.render_res_x)
    builder.add_flag("--height", m.render_res_y)
    builder.add_flag("--materials", ",".join(str(m) for m in materials))

    cmd = builder.build_list()
    c4d = Cinema4D()
    c4d.run_py(cmd, callback=callback)


def repath_textures(
    scene_path: Path,
    nocopy: bool = False,
    callback: Callable[[], None] | None = None,
):
    s = SettingsManager()
    builder = CmdBuilder()
    root = Path(s.CoreSettings.root_path)
    p = root / "scripts" / "repath_textures.py"
    if not p.exists():
        Logger.error(f"Cant find scripts path {p}")
        return

    builder.add_positional(str(p))
    builder.add_flag("--scene", scene_path)
    if nocopy:
        builder.add_flag("--nocopy")

    cmd = builder.build_list()
    c4d = Cinema4D()
    c4d.run_py(cmd, callback=callback)
