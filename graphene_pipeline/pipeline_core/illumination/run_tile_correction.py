from skimage import io
import cv2
import numpy as np


def load_rgb_image(path):
    image = io.imread(path)

    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)

    if image.shape[-1] == 4:
        image = image[:, :, :3]

    return image


def normalize_to_uint8(channel):
    return cv2.normalize(
        channel,
        None,
        0,
        255,
        cv2.NORM_MINMAX,
    ).astype(np.uint8)