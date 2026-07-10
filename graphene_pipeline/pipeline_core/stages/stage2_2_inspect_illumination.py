from pathlib import Path
import argparse
import json
import sys
from datetime import datetime

import numpy as np
import tifffile
from PIL import Image
from skimage import color, exposure
from skimage.filters import gaussian

# =====================================================
# Project bootstrap
# =====================================================

from config import PROJECT_DIR

PROJECT_ROOT = PROJECT_DIR


STITCHED_IMAGE_PATH = PROJECT_ROOT / "data" / "stitched_images" / "Fused.tif"
OUTPUT_DIR = PROJECT_ROOT / "data" / "stage2_outputs"
REPORTS_DIR = PROJECT_ROOT / "reports"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 2.2: inspect stitched illumination.")
    parser.add_argument(
        "--run-config",
        default=None,
        help="Optional runtime config path. Accepted for Stage 7 app compatibility.",
    )
    return parser.parse_args()


def ensure_folders() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def load_rgb_image(path: Path) -> np.ndarray:
    image = tifffile.imread(path)

    if image.ndim == 3 and image.shape[0] in (3, 4):
        image = np.moveaxis(image, 0, -1)

    if image.ndim == 3 and image.shape[-1] == 4:
        image = image[:, :, :3]

    if image.ndim == 2:
        image = np.stack([image, image, image], axis=-1)

    if image.ndim != 3 or image.shape[-1] != 3:
        raise RuntimeError(f"Expected RGB image, got shape {image.shape}")

    if image.dtype != np.uint8:
        image = exposure.rescale_intensity(image, out_range=(0, 255)).astype(np.uint8)

    return image


def save_preview(array: np.ndarray, path: Path, max_width: int = 2000) -> None:
    arr = array.copy()

    if arr.dtype != np.uint8:
        arr = exposure.rescale_intensity(arr, out_range=(0, 255)).astype(np.uint8)

    h, w = arr.shape[:2]
    scale = min(1.0, max_width / w)

    pil = Image.fromarray(arr)

    if scale < 1.0:
        pil = pil.resize((int(w * scale), int(h * scale)))

    pil.save(path)


def estimate_large_scale_illumination(image_rgb: np.ndarray):
    lab = color.rgb2lab(image_rgb)
    L = lab[:, :, 0]
    illumination = gaussian(L, sigma=250, preserve_range=True)
    return L, illumination


def main() -> None:
    parse_args()
    ensure_folders()

    print("Loading stitched image...")
    image_rgb = load_rgb_image(STITCHED_IMAGE_PATH)

    print("Estimating large-scale illumination...")
    L, illumination = estimate_large_scale_illumination(image_rgb)

    illumination_range = float(np.max(illumination) - np.min(illumination))
    illumination_std = float(np.std(illumination))

    illum_path = OUTPUT_DIR / "stitched_estimated_illumination.png"
    save_preview(illumination, illum_path)

    report = {
        "stage": "stage2_2_inspect_illumination",
        "status": "success",
        "input_path": str(STITCHED_IMAGE_PATH),
        "image_shape": list(image_rgb.shape),
        "dtype": str(image_rgb.dtype),
        "illumination_L_min": float(np.min(illumination)),
        "illumination_L_max": float(np.max(illumination)),
        "illumination_L_range": illumination_range,
        "illumination_L_std": illumination_std,
        "illumination_preview": str(illum_path),
        "timestamp": datetime.now().isoformat(),
    }

    report_path = REPORTS_DIR / f"stage2_2_illumination_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)

    print(f"Illumination preview saved to: {illum_path}")
    print(f"Report saved to: {report_path}")
    print(f"L-channel illumination range: {illumination_range:.2f}")
    print(f"L-channel illumination std: {illumination_std:.2f}")
    print("Stage 2.2 illumination inspection complete.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Stage 2.2 failed: {e}")
        sys.exit(1)
