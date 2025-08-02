from pathlib import Path

import cv2
import imageio
import numpy as np

from shared.logger import Logger

imageio.plugins.freeimage.download()


def create_sdr_preview(hdri_path: Path, thumbnail_path: Path, width_size: int):
    if not hdri_path.is_file() or thumbnail_path.exists():
        return thumbnail_path

    if hdri_path.suffix == ".exr":
        image = imageio.imread(str(hdri_path), format="EXR-FI")[:, :, :3]
    elif hdri_path.suffix == ".hdr":
        image = cv2.imread(str(hdri_path), flags=-1)
        if image is None:
            return
    else:
        Logger.error(f"Invalid HDRI file format: {hdri_path.suffix}")
        return

    height, width = image.shape[:2]
    jpg_image = process_img(image, (width_size, int(height / (width / 350))))
    cv2.imwrite(str(thumbnail_path), jpg_image)


def reinhard_tonemap(
    img: cv2.Mat | imageio.core.util.Array, exposure: float = 1.0, white: float = 1.0
):
    return img * (1.0 + (img / (white**2))) / (exposure + img)


def process_img(image: cv2.Mat | imageio.core.util.Array, size: tuple[int, int]):
    res_img = cv2.resize(image, size, interpolation=cv2.INTER_LINEAR)
    tonemapped_image = reinhard_tonemap(res_img)
    gamma_corrected = np.power(tonemapped_image, 1.0 / 2.2)
    jpg_image = np.clip(gamma_corrected * 255, 0, 255).astype(np.uint8)
    return jpg_image
