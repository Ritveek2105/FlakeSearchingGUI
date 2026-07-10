import cv2
import numpy as np


def rgb_to_lab(image_rgb: np.ndarray) -> np.ndarray:
    lab8 = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2LAB)
    lab = lab8.astype(np.float32)
    lab[:, :, 0] *= 100.0 / 255.0
    lab[:, :, 1] -= 128.0
    lab[:, :, 2] -= 128.0
    return lab


def lab_to_rgb(lab: np.ndarray) -> np.ndarray:
    lab8 = np.empty(lab.shape, dtype=np.uint8)
    lab8[:, :, 0] = np.clip(lab[:, :, 0] * 255.0 / 100.0, 0, 255).astype(np.uint8)
    lab8[:, :, 1] = np.clip(lab[:, :, 1] + 128.0, 0, 255).astype(np.uint8)
    lab8[:, :, 2] = np.clip(lab[:, :, 2] + 128.0, 0, 255).astype(np.uint8)
    return cv2.cvtColor(lab8, cv2.COLOR_LAB2RGB)
