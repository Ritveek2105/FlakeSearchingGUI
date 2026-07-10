import base64
import os
from pathlib import Path
from typing import Any, Dict, List

import requests


def _encode_image_base64(image_path: Path) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def run_roboflow_inference(
    image_path: Path,
    model_id: str,
    confidence: float,
    api_url: str,
    api_key: str | None = None,
) -> Dict[str, Any]:
    """
    Run Roboflow hosted inference on one image tile.

    Works with Roboflow detection-style JSON responses.
    """
    if api_key is None:
        api_key = os.environ.get("ROBOFLOW_API_KEY")

    if not api_key:
        raise RuntimeError(
            "Missing Roboflow API key. Set it in PowerShell with:\n"
            '$env:ROBOFLOW_API_KEY="your_key_here"'
        )

    encoded_image = _encode_image_base64(image_path)

    url = f"{api_url.rstrip('/')}/{model_id}"

    params = {
        "api_key": api_key,
        "confidence": confidence,
    }

    response = requests.post(
        url,
        params=params,
        data=encoded_image,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=120,
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"Roboflow request failed for {image_path.name}\n"
            f"Status code: {response.status_code}\n"
            f"Response: {response.text}"
        )

    return response.json()


def convert_predictions_to_global(
    roboflow_result: Dict[str, Any],
    tile_id: str,
    tile_x0: int,
    tile_y0: int,
) -> List[Dict[str, Any]]:
    """
    Convert Roboflow tile-local detections into full stitched-image coordinates.

    Supports common Roboflow bounding-box predictions.
    Also preserves polygon points if they exist.
    """
    output = []

    predictions = roboflow_result.get("predictions", [])

    for i, pred in enumerate(predictions):
        local_x = float(pred.get("x", 0))
        local_y = float(pred.get("y", 0))
        width = float(pred.get("width", 0))
        height = float(pred.get("height", 0))

        global_x = tile_x0 + local_x
        global_y = tile_y0 + local_y

        global_bbox = {
            "x": global_x,
            "y": global_y,
            "width": width,
            "height": height,
            "x_min": global_x - width / 2,
            "y_min": global_y - height / 2,
            "x_max": global_x + width / 2,
            "y_max": global_y + height / 2,
        }

        global_points = None

        if "points" in pred and pred["points"]:
            global_points = [
                {
                    "x": tile_x0 + float(p["x"]),
                    "y": tile_y0 + float(p["y"]),
                }
                for p in pred["points"]
            ]

        detection = {
            "id": None,
            "source_tile": tile_id,
            "source_prediction_index": i,
            "class": pred.get("class", "flake"),
            "confidence": float(pred.get("confidence", 0)),
            "bbox": global_bbox,
            "centroid": {
                "x": global_x,
                "y": global_y,
            },
            "polygon": global_points,
            "raw_prediction": pred,
        }

        output.append(detection)

    return output