import numpy as np
from pipeline_core.illumination.lab_color import lab_to_rgb
def correct_illumination_l_only(lab, illumination_L):
    """
    Correct only the LAB L channel.

    corrected L = original L - local illumination + median illumination
    """

    corrected_lab = lab.copy()

    reference_L = np.median(illumination_L)

    corrected_lab[:, :, 0] = (
        lab[:, :, 0] - illumination_L + reference_L
    )

    corrected_lab[:, :, 0] = np.clip(
        corrected_lab[:, :, 0],
        0,
        100
    )

    return lab_to_rgb(corrected_lab)
