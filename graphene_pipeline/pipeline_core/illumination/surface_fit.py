import numpy as np
import cv2
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter


def _coarse_shape(height: int, width: int, max_side: int | None) -> tuple[int, int, float]:
    if not max_side or max(height, width) <= max_side:
        return height, width, 1.0

    scale = max_side / max(height, width)
    coarse_height = max(8, int(round(height * scale)))
    coarse_width = max(8, int(round(width * scale)))

    return coarse_height, coarse_width, scale


def fit_l_illumination_surface(
    lab,
    bare_points,
    bare_values,
    smoothing_sigma=45,
    max_output_side=None,
):
    """
    Fit only the L-channel illumination surface.
    """

    h, w, _ = lab.shape
    coarse_h, coarse_w, scale = _coarse_shape(h, w, max_output_side)

    if len(bare_points) == 0:
        raise ValueError("Cannot fit illumination surface without bare-chip points.")

    target_x = np.linspace(0, w - 1, coarse_w, dtype=np.float32)
    target_y = np.linspace(0, h - 1, coarse_h, dtype=np.float32)

    grid_x, grid_y = np.meshgrid(
        target_x,
        target_y,
    )

    L_values = bare_values[:, 0]

    surface_L = griddata(
        bare_points,
        L_values,
        (grid_x, grid_y),
        method="linear",
    )

    missing = np.isnan(surface_L)

    if np.any(missing):
        nearest_surface = griddata(
            bare_points,
            L_values,
            (grid_x, grid_y),
            method="nearest",
        )

        surface_L[missing] = nearest_surface[missing]

    surface_L = gaussian_filter(
        surface_L,
        sigma=max(0.1, smoothing_sigma * scale),
    )

    if scale != 1.0:
        surface_L = cv2.resize(
            surface_L.astype(np.float32),
            (w, h),
            interpolation=cv2.INTER_CUBIC,
        )

    return surface_L
