import numpy as np


def inspect_image(image):
    return {
        "shape": list(image.shape),
        "height": int(image.shape[0]),
        "width": int(image.shape[1]),
        "channels": int(image.shape[2]),
        "dtype": str(image.dtype),
        "min_pixel_value": int(np.min(image)),
        "max_pixel_value": int(np.max(image)),
    }