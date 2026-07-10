from pathlib import Path

import numpy as np
import tifffile
from skimage import exposure
from PIL import Image


def load_rgb_tiff(path: Path) -> np.ndarray:
    if not path.exists():
        raise FileNotFoundError(f"Stitched image not found: {path}")

    image = tifffile.imread(path)

    if image.ndim == 3 and image.shape[0] in (3, 4):
        image = np.moveaxis(image, 0, -1)

    if image.ndim == 3 and image.shape[-1] == 4:
        image = image[:, :, :3]

    if image.ndim == 2:
        image = np.stack([image, image, image], axis=-1)

    if image.ndim != 3 or image.shape[-1] != 3:
        raise RuntimeError(f"Expected RGB image, got shape: {image.shape}")

    if image.dtype != np.uint8:
        image = exposure.rescale_intensity(image, out_range=(0, 255)).astype(np.uint8)

    return image


def save_preview(image: np.ndarray, path: Path, max_width: int = 2000) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)

    arr = image.copy()

    if arr.dtype != np.uint8:
        arr = exposure.rescale_intensity(arr, out_range=(0, 255)).astype(np.uint8)

    h, w = arr.shape[:2]
    scale = min(1.0, max_width / w)

    preview = Image.fromarray(arr)

    if scale < 1.0:
        preview = preview.resize((int(w * scale), int(h * scale)))

    preview.save(path)
    return path