from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def save_detection_preview(
    image: np.ndarray,
    detections: List[Dict[str, Any]],
    output_path: Path,
    max_preview_width: int = 2000,
) -> Path:
    """
    Save an annotated preview image with flake boxes and IDs.

    This is for visual checking only.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    img = Image.fromarray(image).convert("RGB")

    original_w, original_h = img.size

    scale = 1.0
    if original_w > max_preview_width:
        scale = max_preview_width / original_w
        preview_h = int(original_h * scale)
        img = img.resize((max_preview_width, preview_h))

    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except Exception:
        font = ImageFont.load_default()

    for det in detections:
        bbox = det["bbox"]

        x_min = bbox["x_min"] * scale
        y_min = bbox["y_min"] * scale
        x_max = bbox["x_max"] * scale
        y_max = bbox["y_max"] * scale

        flake_id = det.get("id", "?")
        conf = det.get("confidence", 0)

        draw.rectangle(
            [x_min, y_min, x_max, y_max],
            outline="red",
            width=2,
        )

        draw.text(
            (x_min, max(0, y_min - 18)),
            f"{flake_id} {conf:.2f}",
            fill="red",
            font=font,
        )

    img.save(output_path)

    return output_path