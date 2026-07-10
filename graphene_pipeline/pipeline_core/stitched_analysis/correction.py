import numpy as np
import tifffile

from pipeline_core.illumination.lab_color import lab_to_rgb, rgb_to_lab


def correct_l_channel(
    image_rgb,
    illumination_L,
    correction_strength=1.0,
):
    """
    Correct large-scale illumination using only the LAB L channel.

    Parameters
    ----------
    image_rgb : ndarray (H, W, 3)
        Original stitched RGB image.

    illumination_L : ndarray (H, W)
        Estimated illumination surface in LAB L space.

    correction_strength : float
        1.0 = full correction
        0.5 = half correction
        0.0 = no correction

    Returns
    -------
    corrected_rgb : ndarray (uint8)
        Illumination-corrected RGB image.

    corrected_lab : ndarray
        Corrected LAB image.
    """

    lab = rgb_to_lab(image_rgb)
    return correct_l_channel_lab(
        lab,
        illumination_L,
        correction_strength=correction_strength,
    )


def correct_l_channel_lab(
    lab,
    illumination_L,
    correction_strength=1.0,
):
    """
    Correct large-scale illumination from an already-computed LAB image.
    """

    L = lab[:, :, 0]
    A = lab[:, :, 1]
    B = lab[:, :, 2]

    # --------------------------------------------
    # Estimate mean illumination
    # --------------------------------------------

    mean_illumination = np.mean(illumination_L)

    # --------------------------------------------
    # Remove illumination trend
    # --------------------------------------------

    corrected_L = (
        L
        - correction_strength * (illumination_L - mean_illumination)
    )

    # --------------------------------------------
    # Keep valid LAB range
    # --------------------------------------------

    corrected_L = np.clip(
        corrected_L,
        0.0,
        100.0,
    )

    # --------------------------------------------
    # Reassemble LAB image
    # --------------------------------------------

    corrected_lab = np.dstack(
        (
            corrected_L,
            A,
            B,
        )
    )

    # --------------------------------------------
    # LAB -> RGB
    # --------------------------------------------

    corrected_rgb = lab_to_rgb(corrected_lab)

    return corrected_rgb, corrected_lab


def save_corrected_tiff(
    corrected_rgb,
    output_path,
):
    """
    Save corrected RGB image as a standard TIFF.
    """

    tifffile.imwrite(
        output_path,
        corrected_rgb,
        photometric="rgb",
        metadata=None,
    )
