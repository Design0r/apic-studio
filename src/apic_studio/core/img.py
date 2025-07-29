from pathlib import Path

import cv2
import imageio
import numpy as np

from shared.logger import Logger


def create_sdr_preview(hdri_path: Path, thumbnail_path: Path, width_size: int):
    if not hdri_path.is_file() or thumbnail_path.exists():
        return thumbnail_path

    if hdri_path.suffix == ".exr":
        imageio.plugins.freeimage.download()
        image = imageio.imread(hdri_path, format="EXR-FI")[:, :, :3]
    elif hdri_path.suffix == ".hdr":
        image = cv2.imread(hdri_path, -1)
    else:
        Logger.error(f"Invalid HDRI file format: {hdri_path.suffix}")
        return

    height, width = image.shape[:2]
    jpg_image = process_img(image, (width_size, int(height / (width / 350))))
    cv2.imwrite(thumbnail_path, jpg_image)


def reinhard_tonemap(img, exposure: float = 1.0, white: float = 1.0):
    return img * (1.0 + (img / (white**2))) / (exposure + img)


def process_img(image, size: tuple[int, int]):
    res_img = cv2.resize(image, size, interpolation=cv2.INTER_LINEAR)
    tonemapped_image = reinhard_tonemap(res_img)
    gamma_corrected = np.power(tonemapped_image, 1.0 / 2.2)
    jpg_image = np.clip(gamma_corrected * 255, 0, 255).astype(np.uint8)
    return jpg_image
