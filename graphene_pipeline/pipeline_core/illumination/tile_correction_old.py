from pathlib import Path

import cv2
import numpy as np
from pipeline_core.illumination.io import (
    load_rgb_image,
    normalize_to_uint8,
)
from pipeline_core.illumination.bare_chip import (
    select_bare_chip_points_grid_blocks,
)
from skimage import color, io
from pipeline_core.illumination.flake_mask import estimate_flake_mask_lab
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter
from pipeline_core.illumination.surface_fit import fit_l_illumination_surface
from pipeline_core.illumination.correction import (
    correct_illumination_l_only,
)
from pipeline_core.illumination.visualization import create_points_overlay
from config import PROJECT_DIR




# -----------------------------
# USER SETTINGS
# -----------------------------


input_folder = PROJECT_DIR / "data" / "raw_tiles"
output_folder = PROJECT_DIR / "data" / "corrected_tiles"
mask_output_folder = PROJECT_DIR / "data" / "flake_masks"
points_output_folder = PROJECT_DIR / "data" / "bare_chip_points"

output_folder.mkdir(exist_ok=True)
mask_output_folder.mkdir(exist_ok=True)
points_output_folder.mkdir(exist_ok=True)

valid_extensions = [".png", ".jpg", ".jpeg", ".tif", ".tiff"]

# Flake mask tuning
color_distance_percentile = 88
morph_gradient_percentile = 88
min_flake_size = 80
hole_size = 150

# Morphology kernel sizes
gradient_kernel_size = 7
close_kernel_size = 9
open_kernel_size = 3
safety_dilation_kernel_size = 9

# Grid-block bare-chip selection
block_size = 80
candidates_per_block = 150
patch_radius = 3
max_texture_allowed = 6
max_bare_points = 8000

# Illumination smoothing
illumination_smoothing_sigma = 45


# -----------------------------
# HELPER FUNCTIONS
# -----------------------------


# -----------------------------
# MAIN BATCH PROCESSING
# -----------------------------

image_paths = [
    p for p in input_folder.iterdir()
    if p.suffix.lower() in valid_extensions
]

image_paths.sort()

if len(image_paths) == 0:
    raise FileNotFoundError("No images found in input_images folder.")

for image_path in image_paths:
    print(f"Processing {image_path.name}")

    image_rgb = load_rgb_image(image_path)

    flake_mask, lab = estimate_flake_mask_lab(image_rgb)

    bare_points, bare_values = select_bare_chip_points_grid_blocks(
        lab,
        flake_mask
    )

    print(f"  Bare-chip points found: {len(bare_points)}")

    if len(bare_points) < 20:
        print(f"  Skipping {image_path.name}: not enough bare-chip points found.")
        continue

    illumination_L = fit_l_illumination_surface(
        lab,
        bare_points,
        bare_values
    )

    corrected_rgb = correct_illumination_l_only(
        lab,
        illumination_L
    )

    points_overlay = create_points_overlay(
        image_rgb,
        bare_points
    )

    corrected_path = output_folder / f"{image_path.stem}_corrected.tif"
    mask_path = mask_output_folder / f"{image_path.stem}_flake_mask.png"
    points_path = points_output_folder / f"{image_path.stem}_bare_points.png"

    io.imsave(corrected_path, corrected_rgb)
    io.imsave(mask_path, (flake_mask.astype(np.uint8) * 255))
    io.imsave(points_path, points_overlay)

print("Done.")
print("Corrected images saved to:", output_folder)
print("Flake masks saved to:", mask_output_folder)
print("Bare-chip point overlays saved to:", points_output_folder)
