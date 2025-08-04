from pathlib import Path
from typing import Protocol

from apic_studio.core import db, fs
from shared.logger import Logger


class PoolManager(Protocol):
    def new(self, name: str, path: Path) -> tuple[str, Path]: ...
    def delete(self, path: Path) -> None: ...
    def open_dir(self, path: Path) -> None: ...
    def get(self) -> dict[str, Path]: ...


class _AssetPoolManager:
    POOL_TYPE = ""

    def new(self, name: str, path: Path) -> tuple[str, Path]:
        full_path = path / name / self.POOL_TYPE
        fs.create_dir(full_path)

        schema = db.DBSchema(name, full_path)
        db.insert(db.Tables(self.POOL_TYPE), schema)

        Logger.info(f"created pool: {name} at {full_path}")

        return name, full_path

    def delete(self, path: Path):
        fs.remove_dir(path.parent)

        schema = db.DBSchema(path.parent.stem, path)
        db.delete(db.Tables(self.POOL_TYPE), schema)

        Logger.info(f"deleted pool: {path.stem} at {path}")

    def get(self) -> dict[str, Path]:
        return db.select(db.Tables(self.POOL_TYPE))

    def open_dir(self, path: Path):
        fs.open_dir(path)


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
