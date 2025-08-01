import shutil
from pathlib import Path
from typing import NamedTuple


class Backup(NamedTuple):
    name: str
    original_name: str
    path: Path
    version: int


AssetBackups = list[Backup]
PoolBackups = list[AssetBackups]


class BackupManager:
    def __init__(self) -> None:
        pass

    def load_from_asset(self, path: Path) -> AssetBackups:
        backup_dir = path / "backups"
        if not backup_dir.exists():
            return []

        backups = [
            Backup(b.stem, path.stem, b, int(b.stem.split("_")[-1]))
            for b in backup_dir.iterdir()
        ]

        return backups

    def load_from_pool(self, path: Path) -> PoolBackups:
        return [b for a in path.iterdir() if (b := self.load_from_asset(a))]

    def create(self, path: Path) -> Backup:
        backup_dir = path.parent / "backups"
        backup_dir.mkdir(exist_ok=True)

        versions: list[Path] = []
        for b in backup_dir.iterdir():
            versions.append(b)

        next_version = len(versions) + 1

        backup_path = (
            path.parent
            / "backups"
            / f"{path.stem}_{self._left_pad(str(next_version), '0')}{path.suffix}"
        )
        shutil.copy2(path, backup_path)
        backup = Backup(backup_path.stem, path.stem, backup_path, next_version)

        return backup

    def _left_pad(self, value: str, pad_value: str, pad: int = 3) -> str:
        if len(value) > pad:
            return value

        return f"{pad_value * (pad - len(value))}{value}"
