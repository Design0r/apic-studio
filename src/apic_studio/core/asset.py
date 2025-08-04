from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PySide6.QtGui import QIcon


class Asset:
    IMG_EXT = (".jpg", ".png")
    CG_EXT = (".c4d", ".hdr", ".exr")
    __slots__ = (
        "path",
        "name",
        "suffix",
        "size",
        "icon",
        "file",
        "metadata",
        "icon_path",
    )

    def __init__(self, file: Path, icon: QIcon, icon_path: Path) -> None:
        self.file = file
        self.path = file.parent
        self.name = file.stem
        self.size = file.stat().st_size
        self.icon = icon
        self.icon_path = icon_path
        self.suffix = file.suffix
        self.metadata: Metadata = Metadata(self.path / f"{self.name}.json")

    def format_size(self) -> str:
        # bytes
        filesize = f"{self.size / 1_000:.2f}KB"
        if self.size >= 100_000_000:
            filesize = f"{self.size / 1_000_000_000:.2f}GB"
        elif self.size >= 100_000:
            filesize = f"{self.size / 1_000_000:.2f}MB"

        return filesize

    def __repr__(self) -> str:
        return f"Asset(path={self.file}, icon={self.icon})"


class Metadata:
    __slots__ = ("notes", "tags", "path")

    def __init__(self, path: Path) -> None:
        self.path = path
        self.notes: str = ""
        self.tags: list[str] = []

    def load(self):
        if not self.path.exists():
            self.save()

        with open(self.path, "r") as f:
            res = json.load(f)
            self.notes = res.get("notes", "")
            self.tags = res.get("tags", [])

    def save(self):
        with open(self.path, "w") as f:
            data: dict[str, Any] = {"notes": self.notes, "tags": self.tags}
            json.dump(data, f)
