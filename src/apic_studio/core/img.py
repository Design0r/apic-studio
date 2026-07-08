from __future__ import annotations

from pathlib import Path
from typing import Optional

import rust_thumbnails

from shared.logger import Logger


def create_sdr_preview(
    hdri_path: Path, thumbnail_path: Path, width_size: int
) -> Optional[Path]:
    if not hdri_path.is_file() or thumbnail_path.exists():
        return thumbnail_path

    try:
        rust_thumbnails.sdr_to_jpg(str(hdri_path), str(thumbnail_path), width_size)
    except Exception as e:
        Logger.exception(e)
        return None

    return thumbnail_path


def downscale_sdr_image(
    img_path: Path, thumbnail_path: Path, width_size: int
) -> Optional[Path]:
    if not img_path.is_file() or thumbnail_path.exists():
        return thumbnail_path

    try:
        rust_thumbnails.downscale_sdr_image(
            str(img_path), str(thumbnail_path), width_size
        )
    except Exception as e:
        Logger.exception(e)
        return None

    return thumbnail_path
