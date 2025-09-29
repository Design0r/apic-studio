from __future__ import annotations

import json
from abc import ABC
from datetime import datetime
from enum import Enum
from pathlib import Path
from socket import gethostname
from typing import Any, TypeVar

from shared.logger import Logger


class Renderer(Enum):
    DEFAULT = 0
    VRAY = 1
    ARNOLD = 2
    REDSHIFT = 3


class Settings(ABC):
    settings: dict[str, type[Settings]] = {}

    def __init__(self):
        self.pools = {}

    def to_dict(self) -> dict[str, Any]:
        return {
            key: value if not isinstance(value, Path) else str(value)
            for key, value in self.__dict__.items()
            if not key.startswith("pools") or not key.startswith("_")
        }

    def from_dict(self, data: dict[str, Any]):
        if not data:
            return

        for key, default in self.__dict__.items():
            if not hasattr(self, key):
                continue
            setattr(self, key, data.get(key, default))


T = TypeVar("T", bound="Settings")


def register(settings: type[T]) -> type[T]:
    setting_name = settings.__name__
    if setting_name not in Settings.settings:
        Settings.settings[setting_name] = settings
        Logger.debug(f"registered settings class {setting_name}")

    return settings


@register
class MaterialSettings(Settings):
    def __init__(self):
        super().__init__()
        self.current_pool = ""
        self.renderer = Renderer.VRAY.value
        self.render_scene = "Path/to/render/scene"
        self.render_object = "shaderball_object"
        self.render_cam = "render_cam"
        self.render_res_x = 350
        self.render_res_y = 350


@register
class ModelSettings(Settings):
    def __init__(self):
        super().__init__()
        self.current_pool = ""
        self.screenshot_opacity = 0.30


@register
class HdriSettings(Settings):
    def __init__(self):
        super().__init__()
        self.current_pool = ""


@register
class LightsetSettings(Settings):
    def __init__(self):
        super().__init__()
        self.current_pool = ""


@register
class WindowSettings(Settings):
    def __init__(self) -> None:
        super().__init__()
        self.window_geometry = [100, 100, 1000, 700]
        self.current_viewport = "materials"


p = Path.home()
print(p)
l = p
print(l, l.exists())


@register
class CoreSettings(Settings):
    def __init__(self) -> None:
        super().__init__()
        self._local = Path.home() / "AppData" / "Local" / "ApicStudio"
        self.socket_addr = "localhost"
        self.socket_port = 1337
        self.root_path = str(Path(__file__).parent.parent.parent)
        self.config_path = str(self._local / f"config-{gethostname()}.json")
        self.db_path = str(Path(self.root_path, "apic_studio.db"))
        self.logs = str(Path(self.root_path, "logs"))
        self.logging_path = str(Path(self.logs, f"{datetime.now().date()}.log"))

    @property
    def address(self) -> tuple[str, int]:
        return (self.socket_addr, self.socket_port)

    def set_root_path(self, value: str):
        self.root_path = value
        self.db_path = str(Path(value, "apic_studio.db"))
        self.logs = str(Path(value, "logs"))
        self.logging_path = str(Path(value, "logs", f"{datetime.now().date()}.log"))


class SettingsManager:
    _instance = None

    CoreSettings: CoreSettings
    WindowSettings: WindowSettings
    MaterialSettings: MaterialSettings
    ModelSettings: ModelSettings
    LightsetSettings: LightsetSettings
    HdriSettings: HdriSettings

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)

            cls._instance._initialized = False

        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        for n, t in Settings.settings.items():
            setattr(self, n, t())

        self._initialized = True

    def load_settings(self):
        cp = Path(self.CoreSettings.config_path)
        if not cp.exists():
            self.save_settings()

        if not cp.exists():
            Logger.error(f"settings path {cp} does not exist")
            return

        with open(cp, "r", encoding="utf-8") as file:
            data = json.load(file)
            self.set_all_settings(data)

        Logger.info(f"loading settings from {cp}")

    def save_settings(self):
        cp = Path(self.CoreSettings.config_path)
        path = Path(cp).parent
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)

        with open(cp, "w", encoding="utf-8") as file:
            data = self.get_all_settings()
            json.dump(data, file, indent=4)

        Logger.info(f"saving settings to {cp}")

    def get_all_settings(self) -> dict[str, Any]:
        return {n: getattr(self, n).to_dict() for n in Settings.settings}

    def set_all_settings(self, data: dict[str, Any]) -> None:
        if not data:
            return

        for k, v in data.items():
            setting = getattr(self, k)
            setting.from_dict(v or {})
