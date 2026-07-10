import cv2
import numpy as np
from skimage.morphology import remove_small_objects, remove_small_holes

from config import TILE_CORRECTION
from pipeline_core.illumination.lab_color import rgb_to_lab
from pipeline_core.illumination.io import normalize_to_uint8


def estimate_flake_mask_lab(image_rgb):
    """
    QUMUS-inspired flake/debris mask.

    White in saved mask = excluded from bare-chip sampling.
    Black in saved mask = possible bare substrate.
    """

    lab = rgb_to_lab(image_rgb)

    L = lab[:, :, 0]
    A = lab[:, :, 1]
    B = lab[:, :, 2]

    L8 = normalize_to_uint8(L)
    A8 = normalize_to_uint8(A)
    B8 = normalize_to_uint8(B)

    gradient_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (
            TILE_CORRECTION["gradient_kernel_size"],
            TILE_CORRECTION["gradient_kernel_size"],
        ),
    )

    grad_L = cv2.morphologyEx(L8, cv2.MORPH_GRADIENT, gradient_kernel)
    grad_A = cv2.morphologyEx(A8, cv2.MORPH_GRADIENT, gradient_kernel)
    grad_B = cv2.morphologyEx(B8, cv2.MORPH_GRADIENT, gradient_kernel)

    combined_gradient = np.maximum.reduce([grad_L, grad_A, grad_B])

    gradient_threshold = np.percentile(
        combined_gradient,
        TILE_CORRECTION["morph_gradient_percentile"],
    )

    edge_mask = combined_gradient > gradient_threshold

    background_lab = np.median(lab.reshape(-1, 3), axis=0)

    color_distance = np.sqrt(
        (L - background_lab[0]) ** 2
        + (A - background_lab[1]) ** 2
        + (B - background_lab[2]) ** 2
    )

    color_threshold = np.percentile(
        color_distance,
        TILE_CORRECTION["color_distance_percentile"],
    )

    color_mask = color_distance > color_threshold

    flake_mask = edge_mask | color_mask

    close_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (
            TILE_CORRECTION["close_kernel_size"],
            TILE_CORRECTION["close_kernel_size"],
        ),
    )

    open_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (
            TILE_CORRECTION["open_kernel_size"],
            TILE_CORRECTION["open_kernel_size"],
        ),
    )

    flake_mask = cv2.morphologyEx(
        flake_mask.astype(np.uint8),
        cv2.MORPH_CLOSE,
        close_kernel,
    ).astype(bool)

    flake_mask = cv2.morphologyEx(
        flake_mask.astype(np.uint8),
        cv2.MORPH_OPEN,
        open_kernel,
    ).astype(bool)

    flake_mask = remove_small_objects(
        flake_mask,
        min_size=TILE_CORRECTION["min_flake_size"],
    )

    flake_mask = remove_small_holes(
        flake_mask,
        area_threshold=TILE_CORRECTION["hole_size"],
    )

    safety_kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (
            TILE_CORRECTION["safety_dilation_kernel_size"],
            TILE_CORRECTION["safety_dilation_kernel_size"],
        ),
    )

    flake_mask = cv2.dilate(
        flake_mask.astype(np.uint8),
        safety_kernel,
        iterations=1,
    ).astype(bool)

    return flake_mask, lab
