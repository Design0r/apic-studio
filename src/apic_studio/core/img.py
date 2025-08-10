from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from shared.logger import Logger

if TYPE_CHECKING:
    import cv2
    import imageio


@lru_cache()
def _cv2():
    import cv2

    return cv2


@lru_cache()
def _np():
    import numpy as np

    return np


@lru_cache()
def _imageio():
    import imageio

    try:
        imageio.plugins.freeimage.download()
    except Exception:
        pass
    return imageio


def create_sdr_preview(
    hdri_path: Path, thumbnail_path: Path, width_size: int
) -> Optional[Path]:
    if not hdri_path.is_file() or thumbnail_path.exists():
        return thumbnail_path

    suffix = hdri_path.suffix.lower()

    if suffix == ".exr":
        imageio = _imageio()
        try:
            image = imageio.imread(str(hdri_path), format="EXR-FI")[:, :, :3]
        except Exception as e:
            Logger.exception(e)
            return
        # BGR <- RGB to match OpenCV expectations later
        image = image[..., ::-1]
    elif suffix == ".hdr":
        cv2 = _cv2()
        try:
            image = cv2.imread(str(hdri_path), flags=-1)
        except Exception as e:
            Logger.exception(e)
            return
        if image is None:
            return
    else:
        Logger.error(f"Invalid HDRI file format: {hdri_path.suffix}")
        return

    height, width = image.shape[:2]
    # Keep aspect ratio relative to the requested width_size (was hard-coded 350 before)
    new_h = int(height * (width_size / width))
    jpg_image = process_img(image, (width_size, new_h))

    cv2 = _cv2()
    cv2.imwrite(str(thumbnail_path), jpg_image)
    return thumbnail_path


def _reinhard_tonemap(img, exposure: float = 1.0, white: float = 1.0):
    img = img * exposure
    return (img * (1 + img / (white * white))) / (1 + img)


def process_img(image: cv2.Mat | imageio.core.util.Array, size: tuple[int, int]):
    cv2 = _cv2()
    np = _np()
    res_img = cv2.resize(image, size, interpolation=cv2.INTER_LINEAR)
    tonemapped_image = _reinhard_tonemap(res_img)
    gamma_corrected = np.power(tonemapped_image, 1.0 / 2.2)
    jpg_image = np.clip(gamma_corrected * 255, 0, 255).astype(np.uint8)
    return jpg_image
