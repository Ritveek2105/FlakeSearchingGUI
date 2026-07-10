from pathlib import Path

import numpy as np
from skimage import io

from pipeline_core.illumination.bare_chip import (
    select_bare_chip_points_grid_blocks,
)
from pipeline_core.illumination.correction import correct_illumination_l_only
from pipeline_core.illumination.flake_mask import estimate_flake_mask_lab
from pipeline_core.illumination.io import load_rgb_image
from pipeline_core.illumination.surface_fit import fit_l_illumination_surface
from pipeline_core.illumination.visualization import create_points_overlay
from config import PROJECT_DIR, TILE_CORRECTION


# -----------------------------
# USER SETTINGS
# -----------------------------

INPUT_FOLDER = PROJECT_DIR / "data" / "raw_tiles"
OUTPUT_FOLDER = PROJECT_DIR / "data" / "corrected_tiles"
MASK_OUTPUT_FOLDER = PROJECT_DIR / "data" / "flake_masks"
POINTS_OUTPUT_FOLDER = PROJECT_DIR / "data" / "bare_chip_points"

VALID_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
MIN_BARE_POINTS = 20


# -----------------------------
# PIPELINE HELPERS
# -----------------------------


def ensure_output_folders():
    """Create output folders if they do not already exist."""
    OUTPUT_FOLDER.mkdir(exist_ok=True)
    MASK_OUTPUT_FOLDER.mkdir(exist_ok=True)
    POINTS_OUTPUT_FOLDER.mkdir(exist_ok=True)


def get_image_paths():
    """Return all valid image paths from the raw tile folder."""
    image_paths = [
        path for path in INPUT_FOLDER.iterdir()
        if path.suffix.lower() in VALID_EXTENSIONS
    ]

    image_paths.sort()

    if len(image_paths) == 0:
        raise FileNotFoundError(f"No images found in {INPUT_FOLDER}")

    return image_paths


def process_tile(image_path):
    """Run the full Stage 1 illumination-correction workflow on one tile."""
    print(f"Processing {image_path.name}")

    image_rgb = load_rgb_image(image_path)

    flake_mask, lab = estimate_flake_mask_lab(image_rgb)

    bare_points, bare_values = select_bare_chip_points_grid_blocks(
        lab,
        flake_mask,
    )

    print(f"  Bare-chip points found: {len(bare_points)}")

    if len(bare_points) < MIN_BARE_POINTS:
        print(f"  Skipping {image_path.name}: not enough bare-chip points found.")
        return False

    illumination_L = fit_l_illumination_surface(
        lab,
        bare_points,
        bare_values,
        smoothing_sigma=TILE_CORRECTION["illumination_smoothing_sigma"],
        max_output_side=TILE_CORRECTION["illumination_surface_max_side"],
    )

    corrected_rgb = correct_illumination_l_only(
        lab,
        illumination_L,
    )

    points_overlay = create_points_overlay(
        image_rgb,
        bare_points,
    )

    corrected_path = OUTPUT_FOLDER / f"{image_path.stem}_corrected.tif"
    mask_path = MASK_OUTPUT_FOLDER / f"{image_path.stem}_flake_mask.png"
    points_path = POINTS_OUTPUT_FOLDER / f"{image_path.stem}_bare_points.png"

    io.imsave(corrected_path, corrected_rgb)
    io.imsave(mask_path, flake_mask.astype(np.uint8) * 255)
    io.imsave(points_path, points_overlay)

    return True
