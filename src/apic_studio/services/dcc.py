import subprocess
import sys
from pathlib import Path
from subprocess import PIPE, Popen
from typing import Any, Callable, Optional, Protocol

from PySide6.QtCore import QObject, QThread

from apic_studio.core.settings import SettingsManager
from shared.logger import Logger
from shared.messaging import Message
from shared.network import Connection


class CmdBuilder:
    def __init__(self) -> None:
        self._cmd: list[str] = []

    def add_positional(self, value: str):
        self._cmd.append(f'"{value}"')

    def add_flag(self, flag: str, value: Any):
        self._cmd.append(flag)
        self._cmd.append(f'"{value}"')

    def build(self) -> str:
        return " ".join(self._cmd)

    def build_list(self) -> list[str]:
        return self._cmd


class DCC(Protocol):
    def get_exe(self) -> Path: ...
    def get_py(self) -> Path: ...
    def version(self) -> str: ...
    def run_exe(self, args: list[str]): ...
    def run_py(self, args: list[str]): ...


class Cinema4D:
    def __init__(self, install_location: Optional[Path] = None) -> None:
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
        loc = self.default_location
        res = list(loc.glob("Maxon Cinema 4D*"))
        latest = res[-1]
        return latest

    def get_exe(self, version: Optional[str]) -> Path:
        return self._get_base() / "Cinema 4D.exe"

    def get_batch(self, version: Optional[str] = None) -> Path:
        return self._get_base() / "Commandline.exe"

    def get_py(self) -> Path:
        return self._get_base() / "c4dpy.exe"

    def run_exe(self, args: list[str]): ...
    def run_py(self, args: list[str], callback: Optional[Callable[[], None]] = None):
        cmd = f"{self.get_py()} {' '.join(args)}"
        rt = RenderThread(cmd)
        self._renders.append(rt)

        def on_finished():
            if callback:
                Logger.info("Finished c4dpy process")
                callback()
            self._renders = []
            rt.deleteLater()

        rt.finished.connect(on_finished)
        Logger.debug(f"Starting c4dpy with cmd: {cmd}")
        rt.start()

    def run_batch(self, args: list[str]):
        cmd = f"{self.get_batch()} {' '.join(args)}"

        subprocess.run(cmd)

    def version(self) -> str: ...


class RenderThread(QThread):
    def __init__(
        self,
        cmd: str,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.cmd = cmd

    def run(self):
        with Popen(self.cmd, stdout=PIPE, stderr=PIPE) as p:
            out, err = p.communicate()
            try:
                Logger.debug(out.decode(errors="ignore"))
                Logger.debug(err.decode(errors="ignore"))
            except UnicodeEncodeError:
                pass
            p.wait()


class DCCBridge:
    def __init__(self, ctx: Connection) -> None:
        self.ctx = ctx

    def is_err(self, msg: Message) -> bool:
        if msg.message == "error":
            return True

        return False

    def call(self, message: str, data: Optional[Any] = None) -> Message:
        msg = Message(message, data=data)
        res = self.ctx.send_recv(msg)
        return Message.from_dict(res)

    def connect(self, address: tuple[str, int]) -> None:
        self.ctx.connect(address)

    def on_connect(self, fn: Callable[[], None]) -> None:
        self.ctx.on_connect(fn)

    def on_disconnect(self, fn: Callable[[], None]) -> None:
        self.ctx.on_disconnect(fn)

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
        self, path: Path, callback: Optional[Callable[[], None]] = None
    ):
        render_material([path], callback=callback)

    def materials_preview_create_all(
        self, path: list[Path], callback: Optional[Callable[[], None]] = None
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

    def file_open(self, path: Path) -> Message:
        res = self.call("core.file.open", {"path": str(path)})
        if self.is_err(res):
            Logger.error(f"failed to open file: {path.name}: {res}")

        return res

    def repath_textures(
        self, path: Path, callback: Optional[Callable[[], None]] = None
    ):
        repath_textures(path, callback=callback)


def render_material(
    materials: list[Path], callback: Optional[Callable[[], None]] = None
):
    builder = CmdBuilder()
    s = SettingsManager()
    m = s.MaterialSettings
    builder.add_positional(str(s.ROOT_PATH.parent / "scripts" / "render_material.py"))

    builder.add_flag("--scene", Path(m.render_scene))
    builder.add_flag("--object", m.render_object)
    builder.add_flag("--camera", m.render_cam)
    builder.add_flag("--width", m.render_res_x)
    builder.add_flag("--height", m.render_res_y)
    builder.add_flag("--materials", ",".join((str(m) for m in materials)))

    cmd = builder.build_list()
    c4d = Cinema4D()
    c4d.run_py(cmd, callback=callback)


def repath_textures(scene_path: Path, callback: Optional[Callable[[], None]] = None):
    s = SettingsManager()
    builder = CmdBuilder()
    builder.add_positional(str(s.ROOT_PATH.parent / "scripts" / "repath_textures.py"))
    builder.add_flag("--scene", scene_path)

    cmd = builder.build_list()
    c4d = Cinema4D()
    c4d.run_py(cmd, callback=callback)
