from pathlib import Path
from typing import Protocol

from apic_studio.core import Logger, db, fs


class PoolManager(Protocol):
    def new(self, path: Path, name: str) -> None: ...
    def delete(self, path: Path) -> None: ...
    def open_dir(self, path: Path) -> None: ...
    def get(self) -> dict[str, Path]: ...


class _AssetPoolManager:
    POOL_TYPE = ""

    def new(self, name: str, path: Path):
        full_path = path / self.POOL_TYPE / name
        fs.create_dir(full_path)

        schema = db.DBSchema(name, path)
        db.insert(db.Tables(self.POOL_TYPE), schema)

        Logger.info(f"created pool: {name} at {full_path}")

    def delete(self, path: Path):
        fs.remove_dir(path)

        schema = db.DBSchema(path.stem, path)
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
