from math import sqrt
from typing import Any, Dict, List


def centroid_distance(det_a: Dict[str, Any], det_b: Dict[str, Any]) -> float:
    ax = det_a["centroid"]["x"]
    ay = det_a["centroid"]["y"]
    bx = det_b["centroid"]["x"]
    by = det_b["centroid"]["y"]

    return sqrt((ax - bx) ** 2 + (ay - by) ** 2)


def merge_duplicate_detections(
    detections: List[Dict[str, Any]],
    duplicate_distance_px: float = 50,
) -> List[Dict[str, Any]]:
    """
    Merge duplicate detections caused by overlapping inference tiles.

    Simple rule:
        If two detections have nearby centroids, keep the higher-confidence one.
    """
    if not detections:
        return []

    detections_sorted = sorted(
        detections,
        key=lambda d: d.get("confidence", 0),
        reverse=True,
    )

    kept = []

    for det in detections_sorted:
        is_duplicate = False

        for kept_det in kept:
            if centroid_distance(det, kept_det) <= duplicate_distance_px:
                is_duplicate = True
                break

        if not is_duplicate:
            kept.append(det)

    for i, det in enumerate(kept, start=1):
        det["id"] = i

    return kept