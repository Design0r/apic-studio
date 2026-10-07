from __future__ import annotations

import json
import os
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Self

from PySide6.QtGui import QImage

from shared.logger import Logger


class Asset:
    SDR_IMG_EXT = (".jpg", ".png")
    HDR_IMG_EXT = (".hdr", ".exr")
    ASSET_EXT = (".c4d", ".dat") + SDR_IMG_EXT + HDR_IMG_EXT
    __slots__ = (
        "file",
        "icon",
        "icon_path",
        "metadata",
        "name",
        "path",
        "size",
        "suffix",
    )

    def __init__(self, file: Path, icon: QImage, icon_path: Path) -> None:
        self.file = file
        self.path = file.parent
        self.name = file.stem
        self.size = file.stat().st_size
        self.icon = icon
        self.icon_path = icon_path
        self.suffix = file.suffix
        self.metadata = Metadata(self.path / f"{self.name}.json")

    def format_size(self) -> str:
        # bytes
        filesize = f"{self.size / 1_000:.2f}KB"
        if self.size >= 100_000_000:
            filesize = f"{self.size / 1_000_000_000:.2f}GB"
        elif self.size >= 100_000:
            filesize = f"{self.size / 1_000_000:.2f}MB"

        return filesize

    def rename(
        self, name: str, create_icon: Callable[[str], QImage] | None = None
    ) -> Self:
        old_file_path = self.file
        new_file_path = self.file.parent / (name + self.file.suffix)
        new_file = self.file.rename(new_file_path)
        new_folder_path = self.file.parent.parent / name
        new_folder = self.file.parent.rename(new_folder_path)

        Logger.info(f"renamed {old_file_path.name} to {self.file.name}")

        try:
            if not str(self.icon_path).startswith(":icons"):
                old_icon_path = new_folder_path / self.icon_path.name
                # keep the "-thumbnail" marker, it is how previews are found
                marker = (
                    "-thumbnail" if old_icon_path.stem.endswith("-thumbnail") else ""
                )
                new_icon_path = old_icon_path.rename(
                    new_folder_path / f"{name}{marker}{self.icon_path.suffix}"
                )
                self.icon_path = new_icon_path
                if create_icon:
                    self.icon = create_icon(str(new_icon_path))
        except Exception as e:
            Logger.exception(e)

        self.path = new_folder
        self.file = new_folder / new_file.name
        self.name = self.file.stem
        self.size = self.file.stat().st_size

        try:
            old_metadata_path = new_folder_path / (old_file_path.stem + ".json")
            new_metadata_path = new_folder_path / (self.file.stem + ".json")
            self.metadata.rename(old_metadata_path, new_metadata_path)
        except Exception as e:
            Logger.exception(e)

        return self

    def __repr__(self) -> str:
        return f"Asset(path={self.file}, icon={self.icon})"


@dataclass(slots=True)
class Metadata:
    path: Path
    notes: str = field(default="")
    tags: list[str] = field(default_factory=list[str])

    def load(self) -> None:
        if not self.path.exists():
            self.save()

        with open(self.path, "r") as f:
            res = json.load(f)
            self.notes = res.get("notes", "")
            self.tags = res.get("tags", [])

        Logger.info(f"loaded metadata for {self.path}")

    def save(self) -> None:
        with open(self.path, "w") as f:
            data: dict[str, Any] = {"notes": self.notes, "tags": self.tags}
            json.dump(data, f)

    def rename(self, old_path: Path, new_path: Path):
        if not old_path.exists():
            return
        self.path = old_path.rename(new_path)
        Logger.info(f"renamed metadata {old_path.name} to {new_path.name}")
        self.load()


def normalize_tag(name: str) -> str:
    """Trim a tag and collapse inner whitespace, "  dark   wood " -> "dark wood"."""
    return " ".join(name.split())


def is_thumbnail_stem(stem: str) -> bool:
    """A generated preview, "<name>-thumbnail", never an asset of its own."""
    return stem.lower().endswith("-thumbnail")


def find_model(folder: Path, names: Iterable[str]) -> Path | None:
    """Pick an asset folder's model file out of the folder's file names.

    Normally it is named after the folder. When it has drifted from that, the
    best match by extension priority wins: a .c4d beats a stray image. Never a
    thumbnail, or its own thumbnail gets thumbnailed on every load and the
    "-thumbnail-thumbnail..." copies pile up.
    """
    names = set(names)
    for ext in Asset.ASSET_EXT:
        name = f"{folder.name}{ext}"
        if name in names:
            return folder / name

    rank = {ext: i for i, ext in enumerate(Asset.ASSET_EXT)}
    candidates: list[tuple[int, str]] = []
    for name in names:
        stem, ext = os.path.splitext(name)
        ext = ext.lower()
        if ext in rank and not is_thumbnail_stem(stem):
            candidates.append((rank[ext], name))

    if not candidates:
        return None

    return folder / min(candidates)[1]


def _is_loose_file(asset: Path) -> bool:
    return asset.suffix.lower() in Asset.ASSET_EXT


def metadata_path(asset: Path) -> Path:
    """Where an asset keeps its notes and tags, see Asset.metadata.

    `asset` is what the pool scan hands out: an asset folder, or a loose file
    sitting directly in the pool. The file is named after the model, which
    for a folder means reading it to find out which file that is.
    """
    if _is_loose_file(asset):
        return asset.parent / f"{asset.stem}.json"

    try:
        model = find_model(asset, os.listdir(asset))
    except OSError:
        model = None

    stem = model.stem if model is not None else asset.name
    return asset / f"{stem}.json"


def _load_json(path: Path) -> Any:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except OSError, ValueError:
        return None


def read_tags(asset: Path) -> frozenset[str]:
    """An asset's tags straight from its metadata file, empty if it has none."""
    # Try the usual name first, decided by name alone: on a network pool the
    # directory read metadata_path needs would double the round trips, and
    # it is only wanted for a model that has drifted from its folder name.
    if _is_loose_file(asset):
        data = _load_json(asset.parent / f"{asset.stem}.json")
    else:
        named = asset / f"{asset.name}.json"
        data = _load_json(named)
        if data is None:
            resolved = metadata_path(asset)
            if resolved != named:
                data = _load_json(resolved)

    tags = data.get("tags") if isinstance(data, dict) else None
    if not isinstance(tags, list):
        return frozenset()

    return frozenset(t for t in tags if isinstance(t, str))
