import json
import re
import argparse
from pathlib import Path

import cv2
import numpy as np
import tifffile as tiff


IMAGE_EXTENSIONS = [".tif", ".tiff", ".png", ".jpg", ".jpeg"]


def load_image(path):
    path = Path(path)

    if path.suffix.lower() in [".tif", ".tiff"]:
        img = tiff.imread(str(path))
    else:
        img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if img is None:
            raise ValueError(f"Could not read image: {path}")
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)

    if img.shape[-1] == 4:
        img = img[:, :, :3]

    if img.dtype != np.uint8:
        img = img.astype(np.float32)
        img -= img.min()
        img /= max(img.max(), 1e-6)
        img = (img * 255).astype(np.uint8)

    return img


def object_pixels(image, contour):
    x, y, w, h = cv2.boundingRect(contour)
    roi = image[y:y + h, x:x + w]

    mask = np.zeros((h, w), dtype=np.uint8)
    shifted = contour - np.array([[[x, y]]])
    cv2.drawContours(mask, [shifted], -1, 255, -1)

    return roi[mask > 0]


def compute_features(img, lab, gray, contour):
    area = cv2.contourArea(contour)
    x, y, w, h = cv2.boundingRect(contour)
    perimeter = cv2.arcLength(contour, True)

    hull = cv2.convexHull(contour)
    hull_area = cv2.contourArea(hull)

    solidity = area / max(hull_area, 1)
    extent = area / max(w * h, 1)
    aspect_ratio = max(w / max(h, 1), h / max(w, 1))
    circularity = 4 * np.pi * area / max(perimeter ** 2, 1e-6)
    perimeter_area_ratio = perimeter / max(area, 1)

    rgb_pixels = object_pixels(img, contour)
    lab_pixels = object_pixels(lab, contour)

    mean_rgb = np.mean(rgb_pixels, axis=0)
    mean_lab = np.mean(lab_pixels, axis=0)
    std_lab = np.std(lab_pixels, axis=0)

    R, G, B_rgb = mean_rgb
    L, A, B_lab = mean_lab

    purple_score = 0

    if A > 132:
        purple_score += 1
    if B_lab < 150:
        purple_score += 1
    if R > G:
        purple_score += 1
    if B_rgb > G:
        purple_score += 1
    if (A - B_lab) > -10:
        purple_score += 1

    roi_gray = gray[y:y + h, x:x + w]
    edges = cv2.Canny(roi_gray, 35, 100)

    obj_mask = np.zeros((h, w), dtype=np.uint8)
    shifted = contour - np.array([[[x, y]]])
    cv2.drawContours(obj_mask, [shifted], -1, 255, -1)

    edge_density = np.logical_and(edges > 0, obj_mask > 0).sum() / max((obj_mask > 0).sum(), 1)

    glue_score = 0

    if solidity < 0.50:
        glue_score += 2
    if extent < 0.22:
        glue_score += 1
    if perimeter_area_ratio > 0.22:
        glue_score += 1
    if aspect_ratio > 8:
        glue_score += 1
    if area > 900 and solidity < 0.65:
        glue_score += 1
    if edge_density < 0.006 and area > 500:
        glue_score += 1

    flake_score = purple_score + (2 if solidity > 0.60 else 0) + (1 if extent > 0.22 else 0) - glue_score

    return {
        "bbox": {
            "x": int(x),
            "y": int(y),
            "width": int(w),
            "height": int(h),
        },
        "area_px": round(float(area), 2),
        "perimeter": round(float(perimeter), 2),
        "solidity": round(float(solidity), 3),
        "extent": round(float(extent), 3),
        "aspect_ratio": round(float(aspect_ratio), 3),
        "circularity": round(float(circularity), 3),
        "perimeter_area_ratio": round(float(perimeter_area_ratio), 4),
        "edge_density": round(float(edge_density), 4),
        "mean_rgb": [round(float(v), 2) for v in mean_rgb],
        "mean_lab": [round(float(v), 2) for v in mean_lab],
        "std_lab": [round(float(v), 2) for v in std_lab],
        "purple_score": int(purple_score),
        "glue_score": int(glue_score),
        "flake_score": int(flake_score),
    }


def detect_purple_flakes(
    img,
    min_area=20,
    max_area=8000,
    threshold=10,
    blur=201,
    min_flake_score=1,
    min_solidity=0.2,
    max_glue_score=6,
):
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    if blur % 2 == 0:
        blur += 1

    bg = cv2.GaussianBlur(lab, (blur, blur), 0)

    diff = lab.astype(np.float32) - bg.astype(np.float32)
    dist = np.sqrt(np.sum(diff ** 2, axis=2))

    L, A, B = cv2.split(lab)

    purple_mask = ((A > 128) & (B < 155)).astype(np.uint8) * 255
    contrast_mask = (dist > threshold).astype(np.uint8) * 255

    mask = cv2.bitwise_or(purple_mask, contrast_mask)

    small_kernel = np.ones((3, 3), np.uint8)
    medium_kernel = np.ones((5, 5), np.uint8)

    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, small_kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, medium_kernel, iterations=1)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    flakes = []
    rejected = {
        "too_small": 0,
        "too_large": 0,
        "low_solidity": 0,
        "glue_like": 0,
        "low_flake_score": 0,
    }

    for contour in contours:
        area = cv2.contourArea(contour)

        if area < min_area:
            rejected["too_small"] += 1
            continue

        if area > max_area:
            rejected["too_large"] += 1
            continue

        features = compute_features(img, lab, gray, contour)

        if features["solidity"] < min_solidity:
            rejected["low_solidity"] += 1
            continue

        if features["glue_score"] > max_glue_score:
            rejected["glue_like"] += 1
            continue

        if features["flake_score"] < min_flake_score:
            rejected["low_flake_score"] += 1
            continue

        M = cv2.moments(contour)

        if M["m00"] == 0:
            bbox = features["bbox"]
            cx = bbox["x"] + bbox["width"] / 2
            cy = bbox["y"] + bbox["height"] / 2
        else:
            cx = M["m10"] / M["m00"]
            cy = M["m01"] / M["m00"]

        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.004 * perimeter, True)
        polygon = approx.reshape(-1, 2).tolist()

        flakes.append({
            "id": f"tile_flake_{len(flakes) + 1:05d}",
            "x": round(float(cx), 2),
            "y": round(float(cy), 2),
            "label": "purple_candidate",
            "polygon": polygon,
            **features,
        })

    return flakes, mask, rejected


def save_tile_preview(img, flakes, path):
    preview = img.copy()

    for flake in flakes:
        bbox = flake["bbox"]
        x1 = bbox["x"]
        y1 = bbox["y"]
        x2 = x1 + bbox["width"]
        y2 = y1 + bbox["height"]

        cv2.rectangle(preview, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.circle(preview, (int(flake["x"]), int(flake["y"])), 4, (255, 0, 0), -1)

    cv2.imwrite(str(path), cv2.cvtColor(preview, cv2.COLOR_RGB2BGR))


def detect_folder(args):
    tile_dir = Path(args.tile_dir)
    out_dir = Path(args.tile_json_dir)
    preview_dir = Path(args.preview_dir)

    out_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)

    image_paths = [
        p for p in sorted(tile_dir.iterdir())
        if p.suffix.lower() in IMAGE_EXTENSIONS
    ]

    summary = []

    for image_path in image_paths:
        print(f"Processing {image_path.name}...")

        img = load_image(image_path)

        flakes, mask, rejected = detect_purple_flakes(
            img,
            min_area=args.min_area,
            max_area=args.max_area,
            threshold=args.threshold,
            blur=args.blur,
            min_flake_score=args.min_flake_score,
            min_solidity=args.min_solidity,
            max_glue_score=args.max_glue_score,
        )

        tile_output = {
            "tile_name": image_path.name,
            "image_width": img.shape[1],
            "image_height": img.shape[0],
            "flake_count": len(flakes),
            "settings": {
                "min_area": args.min_area,
                "max_area": args.max_area,
                "threshold": args.threshold,
                "blur": args.blur,
                "min_flake_score": args.min_flake_score,
                "min_solidity": args.min_solidity,
                "max_glue_score": args.max_glue_score,
            },
            "rejected_counts": rejected,
            "flakes": flakes,
        }

        json_path = out_dir / f"{image_path.stem}.json"

        with open(json_path, "w") as f:
            json.dump(tile_output, f, indent=2)

        if args.save_previews:
            preview_path = preview_dir / f"{image_path.stem}_preview.png"
            save_tile_preview(img, flakes, preview_path)

        summary.append({
            "tile_name": image_path.name,
            "flake_count": len(flakes),
            "json": str(json_path),
        })

    summary_path = out_dir / "_tile_detection_summary.json"

    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print()
    print(f"Processed {len(image_paths)} tile images")
    print(f"Saved tile JSON files to: {out_dir}")
    print(f"Saved summary to: {summary_path}")
    print()


def parse_tile_configuration(path):
    path = Path(path)
    tile_offsets = {}

    pattern = re.compile(
        r"(?P<filename>[^;]+);\s*;\s*\((?P<x>[-+]?\d*\.?\d+),\s*(?P<y>[-+]?\d*\.?\d+)\)"
    )

    with open(path, "r") as f:
        for line in f:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            match = pattern.search(line)

            if match:
                filename = Path(match.group("filename").strip()).name
                x = float(match.group("x"))
                y = float(match.group("y"))
                tile_offsets[filename] = {"x_offset": x, "y_offset": y}

    return tile_offsets


def merge_duplicate_flakes(flakes, distance_px=50):
    kept = []

    flakes = sorted(flakes, key=lambda f: f.get("flake_score", 0), reverse=True)

    for flake in flakes:
        fx = flake["x"]
        fy = flake["y"]

        duplicate = False

        for kept_flake in kept:
            dx = fx - kept_flake["x"]
            dy = fy - kept_flake["y"]

            if np.sqrt(dx * dx + dy * dy) < distance_px:
                duplicate = True
                break

        if not duplicate:
            kept.append(flake)

    kept = sorted(kept, key=lambda f: f["id"])

    for i, flake in enumerate(kept, start=1):
        flake["id"] = f"flake_{i:05d}"

    return kept


def merge_tile_jsons(args):
    tile_json_dir = Path(args.tile_json_dir)
    tile_config = Path(args.tile_config)
    output_json = Path(args.output_json)

    offsets = parse_tile_configuration(tile_config)

    all_flakes = []
    missing_tiles = []

    json_files = [
        p for p in sorted(tile_json_dir.iterdir())
        if p.suffix.lower() == ".json" and not p.name.startswith("_")
    ]

    for json_path in json_files:
        with open(json_path, "r") as f:
            tile_data = json.load(f)

        tile_name = tile_data["tile_name"]
        tile_base = Path(tile_name).name

        if tile_base not in offsets:
            missing_tiles.append(tile_base)
            continue

        x_offset = offsets[tile_base]["x_offset"]
        y_offset = offsets[tile_base]["y_offset"]

        for flake in tile_data["flakes"]:
            stitched_flake = dict(flake)

            stitched_flake["source_tile"] = tile_base
            stitched_flake["tile_x"] = flake["x"]
            stitched_flake["tile_y"] = flake["y"]

            stitched_flake["x"] = round(float(flake["x"] + x_offset), 2)
            stitched_flake["y"] = round(float(flake["y"] + y_offset), 2)

            stitched_flake["bbox"] = {
                "x": int(round(flake["bbox"]["x"] + x_offset)),
                "y": int(round(flake["bbox"]["y"] + y_offset)),
                "width": flake["bbox"]["width"],
                "height": flake["bbox"]["height"],
            }

            stitched_polygon = []
            for px, py in flake["polygon"]:
                stitched_polygon.append([
                    round(float(px + x_offset), 2),
                    round(float(py + y_offset), 2),
                ])

            stitched_flake["polygon"] = stitched_polygon

            all_flakes.append(stitched_flake)

    before_dedup = len(all_flakes)

    if args.deduplicate:
        all_flakes = merge_duplicate_flakes(all_flakes, distance_px=args.duplicate_distance)

    output = {
        "coordinate_system": "stitched_image_pixels",
        "tile_config_file": str(tile_config),
        "tile_json_dir": str(tile_json_dir),
        "flake_count": len(all_flakes),
        "flake_count_before_deduplication": before_dedup,
        "duplicate_distance_px": args.duplicate_distance if args.deduplicate else None,
        "missing_tiles_from_tile_config": missing_tiles,
        "flakes": all_flakes,
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)

    with open(output_json, "w") as f:
        json.dump(output, f, indent=2)

    print()
    print(f"Merged tile JSON files: {len(json_files)}")
    print(f"Flakes before duplicate removal: {before_dedup}")
    print(f"Final flakes: {len(all_flakes)}")
    print(f"Saved stitched JSON: {output_json}")

    if missing_tiles:
        print()
        print("Warning: These tile JSON files were not found in TileConfiguration:")
        for tile in missing_tiles:
            print(f"  {tile}")

    print()


def main():
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(dest="command", required=True)

    detect_parser = subparsers.add_parser("detect-folder")
    detect_parser.add_argument("--tile-dir", required=True)
    detect_parser.add_argument("--tile-json-dir", default="tile_json")
    detect_parser.add_argument("--preview-dir", default="tile_previews")
    detect_parser.add_argument("--save-previews", action="store_true")

    detect_parser.add_argument("--min-area", type=float, default=20)
    detect_parser.add_argument("--max-area", type=float, default=8000)
    detect_parser.add_argument("--threshold", type=float, default=10)
    detect_parser.add_argument("--blur", type=int, default=201)
    detect_parser.add_argument("--min-flake-score", type=int, default=1)
    detect_parser.add_argument("--min-solidity", type=float, default=0.2)
    detect_parser.add_argument("--max-glue-score", type=int, default=6)

    merge_parser = subparsers.add_parser("merge")
    merge_parser.add_argument("--tile-json-dir", required=True)
    merge_parser.add_argument("--tile-config", required=True)
    merge_parser.add_argument("--output-json", default="public/flakes.json")
    merge_parser.add_argument("--deduplicate", action="store_true")
    merge_parser.add_argument("--duplicate-distance", type=float, default=50)

    args = parser.parse_args()

    if args.command == "detect-folder":
        detect_folder(args)
    elif args.command == "merge":
        merge_tile_jsons(args)


if __name__ == "__main__":
    main()