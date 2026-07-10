import numpy as np
import cv2
from pipeline_core.illumination.io import normalize_to_uint8

def create_points_overlay(image_rgb, bare_points):
    """
    Save a visual check image showing selected bare-chip points.
    """

    overlay = image_rgb.copy()

    if overlay.dtype != np.uint8:
        overlay = normalize_to_uint8(overlay)

    overlay_bgr = cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR)

    for x, y in bare_points:
        cv2.circle(
            overlay_bgr,
            (int(x), int(y)),
            2,
            (0, 255, 0),
            -1
        )

    overlay_rgb = cv2.cvtColor(overlay_bgr, cv2.COLOR_BGR2RGB)

    return overlay_rgb