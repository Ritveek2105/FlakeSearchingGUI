import numpy as np
from skimage import exposure

from config import STITCHED_ANALYSIS
from pipeline_core.illumination.flake_mask import estimate_flake_mask_lab
from pipeline_core.illumination.bare_chip import select_bare_chip_points_grid_blocks
from pipeline_core.illumination.surface_fit import fit_l_illumination_surface
from pipeline_core.illumination.visualization import create_points_overlay


# ==========================================================
# Stage 2 stitched-image illumination settings
# (These will eventually move into config.py.)
# ==========================================================

BLOCK_SIZE = 400
CANDIDATES_PER_BLOCK = 300
PATCH_RADIUS = 6
MAX_TEXTURE_ALLOWED = 8
MAX_BARE_POINTS = 30000

ILLUMINATION_SMOOTHING_SIGMA = 180


def estimate_stitched_illumination(image_rgb):
    """
    Estimate stitched-image illumination using the same algorithm
    as Stage 1, but with parameters tuned for much larger mosaics.
    """

    print("Generating stitched-image flake mask...")

    flake_mask, lab = estimate_flake_mask_lab(image_rgb)

    print("Selecting bare-chip points...")

    bare_points, bare_values = select_bare_chip_points_grid_blocks(
        lab,
        flake_mask,
        block_size=BLOCK_SIZE,
        candidates_per_block=CANDIDATES_PER_BLOCK,
        patch_radius=PATCH_RADIUS,
        max_texture_allowed=MAX_TEXTURE_ALLOWED,
        max_bare_points=MAX_BARE_POINTS,
    )

    print(f"Selected {len(bare_points)} bare-chip points.")

    print("Fitting illumination surface...")

    illumination_L = fit_l_illumination_surface(
        lab,
        bare_points,
        bare_values,
        smoothing_sigma=ILLUMINATION_SMOOTHING_SIGMA,
        max_output_side=STITCHED_ANALYSIS["illumination_surface_max_side"],
    )

    print("Creating diagnostic overlay...")

    bare_points_overlay = create_points_overlay(
        image_rgb,
        bare_points,
    )

    return {
        "lab": lab,
        "flake_mask": flake_mask,
        "bare_points": bare_points,
        "bare_values": bare_values,
        "illumination_L": illumination_L,
        "bare_points_overlay": bare_points_overlay,
    }


def normalize_to_uint8(image):
    """
    Convert floating-point images to uint8 for visualization.
    """
    return exposure.rescale_intensity(
        image,
        out_range=(0, 255),
    ).astype(np.uint8)


def mask_to_uint8(mask):
    """
    Convert boolean mask to uint8 image.
    """
    return (mask.astype(np.uint8) * 255)
