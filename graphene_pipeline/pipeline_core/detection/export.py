import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def save_tile_json(
    result: Dict[str, Any],
    tile_id: str,
    output_dir: Path,
) -> Path:
    """
    Save raw Roboflow result for one tile.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    path = output_dir / f"{tile_id}.json"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    return path


def save_flakes_json(
    detections: List[Dict[str, Any]],
    output_path: Path,
    image_name: str,
    image_width: int,
    image_height: int,
    model_id: str,
) -> Path:
    """
    Save final merged detection results.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "metadata": {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "stage": "stage3_detect_flakes",
            "image_name": image_name,
            "image_width": image_width,
            "image_height": image_height,
            "model_id": model_id,
            "detection_count": len(detections),
        },
        "flakes": detections,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return output_path