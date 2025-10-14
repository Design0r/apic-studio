import shutil
from dataclasses import dataclass
from pathlib import Path

from shared.logger import Logger


@dataclass(slots=True)
class Backup:
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

    def rename_from_asset(self, path: Path, new_name: str) -> AssetBackups:
        backups = self.load_from_asset(path)
        for b in backups:
            new_backup = b.path.rename(
                b.path.parent
                / (f"{new_name}_{b.path.stem.split('_').pop()}{b.path.suffix}")
            )
            Logger.info(f"renamed backup {b.path.name} to {new_backup.name}")

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

        Logger.info(f"created backup {backup_path.name}")

        return backup

    def _left_pad(self, value: str, pad_value: str, pad: int = 3) -> str:
        if len(value) > pad:
            return value

        return f"{pad_value * (pad - len(value))}{value}"
