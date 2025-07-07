from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon


class Asset:
    IMG_EXT = (".jpg", ".png")
    CG_EXT = (".c4d",)
    __slots__ = ("path", "name", "suffix", "size", "icon", "file")

    def __init__(self, file: Path, icon: QIcon) -> None:
        self.file = file
        self.path = file.parent
        self.name = file.stem
        self.size = file.stat().st_size
        self.icon = icon
        self.suffix = file.suffix

    def __repr__(self) -> str:
        return f"Asset(path={self.file}, icon={self.icon})"
