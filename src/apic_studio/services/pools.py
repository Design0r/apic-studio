from pathlib import Path
from typing import Any, Protocol

from apic_studio.core import db, fs
from shared.logger import Logger
from shared.messaging import Message
from shared.network import Connection


class PoolManager(Protocol):
    def new(self, name: str, path: Path) -> tuple[str, Path]: ...
    def delete(self, path: Path) -> None: ...
    def open_dir(self, path: Path) -> None: ...
    def get(self) -> dict[str, Path]: ...
    def save(self, path: Path) -> dict[str, Any]: ...
    def export(self, path: Path) -> dict[str, Any]: ...
    def copy_textures(self, path: Path) -> None: ...


class _AssetPoolManager:
    POOL_TYPE = ""

    def __init__(self, ctx: Connection):
        self.ctx = ctx

    def new(self, name: str, path: Path) -> tuple[str, Path]:
        full_path = path / name / self.POOL_TYPE
        fs.create_dir(full_path)

        schema = db.DBSchema(name, full_path)
        db.insert(db.Tables(self.POOL_TYPE), schema)

        Logger.info(f"created pool: {name} at {full_path}")

        return name, full_path

    def delete(self, path: Path):
        fs.remove_dir(path)

        schema = db.DBSchema(path.stem, path)
        db.delete(db.Tables(self.POOL_TYPE), schema)

        Logger.info(f"deleted pool: {path.stem} at {path}")

    def get(self) -> dict[str, Path]:
        return db.select(db.Tables(self.POOL_TYPE))

    def open_dir(self, path: Path):
        fs.open_dir(path)

    def export(self, path: Path) -> dict[str, Any]:
        res = self.ctx.send_recv(
            Message(f"{self.POOL_TYPE}.export.selected", {"path": str(path)})
        )
        msg = Message.from_dict(res)
        if msg.message != "success":
            Logger.error(
                f"failed to export {self.POOL_TYPE} asset: {path.name} to {path}: {msg.message} {msg.data}"
            )
            return {}

        Logger.info(f"exported {self.POOL_TYPE} asset: {path.name} to {path}")
        return res

    def save(self, path: Path) -> dict[str, Any]:
        res = self.ctx.send_recv(Message(f"{self.POOL_TYPE}.save", {"path": str(path)}))
        msg = Message.from_dict(res)
        if msg.message != "success":
            Logger.error(
                f"failed to save {self.POOL_TYPE} asset: {path.name} to {path}: {msg.message} {msg.data}"
            )
            return {}
        Logger.info(f"saved {self.POOL_TYPE} asset: {path.name} to {path}")
        return res

    def copy_textures(self, path: Path):
        Logger.info(f"Copying textures for {path.name} to {path}")
        pass


class ModelPoolManager(_AssetPoolManager):
    POOL_TYPE = "models"


class MaterialPoolManager(_AssetPoolManager):
    POOL_TYPE = "materials"


class LightsetPoolManager(_AssetPoolManager):
    POOL_TYPE = "lightsets"


class HdriPoolManager(_AssetPoolManager):
    POOL_TYPE = "hdris"


class UtilityPoolManager(_AssetPoolManager):
    POOL_TYPE = "utilities"
