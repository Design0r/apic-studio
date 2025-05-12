from __future__ import annotations

import json
from abc import ABC
from datetime import datetime
from enum import Enum
from pathlib import Path
from socket import gethostname
from typing import Any, TypeVar

from .logger import Logger


class Renderer(Enum):
    DEFAULT = 0
    VRAY = 1
    ARNOLD = 2
    REDSHIFT = 3


class Settings(ABC):
    settings: dict[str, type[Settings]] = {}

    def __init__(self):
        self.pools = {}
        self.current_pool = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in self.__dict__.items()
            if not key.startswith("pools")
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
        Logger.debug(f"Registered settings class {setting_name}")

    return settings


@register
class MaterialSettings(Settings):
    def __init__(self):
        super().__init__()
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
        self.screenshot_opacity = 0.30


@register
class HdriSettings(Settings):
    def __init__(self):
        super().__init__()
        self.hdri_renderer = Renderer.VRAY.value
        self.auto_generate_thumbnails = True


@register
class LightsetSettings(Settings):
    def __init__(self):
        super().__init__()


@register
class WindowSettings(Settings):
    def __init__(self) -> None:
        super().__init__()
        self.window_geometry = [100, 100, 1000, 700]
        self.current_viewport = 0
        self.asset_button_size = 350
        self.ui_scale = 1
        self.socket_addr = ("localhost", 65432)


class SettingsManager:
    _instance = None

    WindowSettings: WindowSettings
    MaterialSettings: MaterialSettings
    ModelSettings: ModelSettings
    LightsetSettings: LightsetSettings
    HdriSettings: HdriSettings

    ROOT_PATH = Path(__file__).parent.parent.parent
    CONFIG_PATH = ROOT_PATH / f"settings/config-{gethostname()}.json"
    DB_PATH = ROOT_PATH / "db" / "apic_studio.db"
    LOGS = ROOT_PATH / "logs"
    LOGGING_PATH = LOGS / f"{datetime.now().date()}.log"

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
        if not self.CONFIG_PATH.exists():
            self.save_settings()

        if not self.CONFIG_PATH.exists():
            Logger.error(f"settings path {self.CONFIG_PATH} does not exist")
            return

        with open(self.CONFIG_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)
            self.set_all_settings(data)

        Logger.info(f"loading settings from {self.CONFIG_PATH}")

    def save_settings(self):
        path = Path(self.CONFIG_PATH).parent
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)

        with open(self.CONFIG_PATH, "w", encoding="utf-8") as file:
            data = self.get_all_settings()
            json.dump(data, file, indent=4)

        Logger.info(f"saving settings to {self.CONFIG_PATH}")

    def get_all_settings(self) -> dict[str, Any]:
        return {n: getattr(self, n).to_dict() for n in Settings.settings}

    def set_all_settings(self, data: dict[str, Any]) -> None:
        if not data:
            return

        for k, v in data.items():
            setting = getattr(self, k)
            setting.from_dict(v or {})
