import os
import json
import re
import argparse
from pathlib import Path

import cv2
import numpy as np
from inference_sdk import InferenceHTTPClient


IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".tif", ".tiff"]


def roboflow_client(api_key):
    return InferenceHTTPClient(
        api_url="https://detect.roboflow.com",
        api_key=api_key,
    )


def run_detection_on_folder(args):
    tile_dir = Path(args.tile_dir)
    out_dir = Path(args.tile_json_dir)
    preview_dir = Path(args.preview_dir)

    out_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)

    api_key = args.api_key or os.environ.get("ROBOFLOW_API_KEY")
    if not api_key:
        raise ValueError("No API key found. Use --api-key or set ROBOFLOW_API_KEY.")

    client = roboflow_client(api_key)

    image_paths = [
        p for p in sorted(tile_dir.iterdir())
        if p.suffix.lower() in IMAGE_EXTENSIONS
    ]

    summary = []

    for image_path in image_paths:
        print(f"Running Roboflow on {image_path.name}...")

        result = client.infer(
            str(image_path),
            model_id=args.model_id,
        )

        img = cv2.imread(str(image_path))
        if img is None:
            print(f"Could not read {image_path.name}, skipping preview.")
            continue

        flakes = []

        for i, pred in enumerate(result.get("predictions", []), start=1):
            conf = float(pred.get("confidence", 0))

            if conf < args.confidence:
                continue

            cx = float(pred["x"])
            cy = float(pred["y"])
            w = float(pred["width"])
            h = float(pred["height"])

            x1 = int(round(cx - w / 2))
            y1 = int(round(cy - h / 2))
            x2 = int(round(cx + w / 2))
            y2 = int(round(cy + h / 2))

            flake = {
                "id": f"tile_flake_{len(flakes)+1:05d}",
                "x": round(cx, 2),
                "y": round(cy, 2),
                "label": pred.get("class", "roboflow_flake"),
                "confidence": round(conf, 4),
                "bbox": {
                    "x": x1,
                    "y": y1,
                    "width": int(round(w)),
                    "height": int(round(h)),
                },
                "polygon": [
                    [x1, y1],
                    [x2, y1],
                    [x2, y2],
                    [x1, y2],
                ],
            }

            flakes.append(flake)

            if args.save_previews:
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(
                    img,
                    f"{flake['label']} {conf:.2f}",
                    (x1, max(0, y1 - 5)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (0, 255, 0),
                    1,
                    cv2.LINE_AA,
                )

        tile_output = {
            "tile_name": image_path.name,
            "flake_count": len(flakes),
            "model_id": args.model_id,
            "confidence_threshold": args.confidence,
            "flakes": flakes,
        }

        json_path = out_dir / f"{image_path.stem}.json"
        with open(json_path, "w") as f:
            json.dump(tile_output, f, indent=2)

        if args.save_previews:
            preview_path = preview_dir / f"{image_path.stem}_preview.png"
            cv2.imwrite(str(preview_path), img)

        summary.append({
            "tile_name": image_path.name,
            "flake_count": len(flakes),
            "json": str(json_path),
        })

    with open(out_dir / "_roboflow_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"Processed {len(image_paths)} images.")
    print(f"Saved tile JSON files to {out_dir}")


def parse_tile_configuration(path):
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
                tile_offsets[filename] = {
                    "x_offset": float(match.group("x")),
                    "y_offset": float(match.group("y")),
                }

    return tile_offsets


def remove_duplicates(flakes, distance_px):
    kept = []

    flakes = sorted(flakes, key=lambda f: f.get("confidence", 0), reverse=True)

    for flake in flakes:
        duplicate = False

        for kept_flake in kept:
            dx = flake["x"] - kept_flake["x"]
            dy = flake["y"] - kept_flake["y"]

            if np.sqrt(dx * dx + dy * dy) < distance_px:
                duplicate = True
                break

        if not duplicate:
            kept.append(flake)

    for i, flake in enumerate(kept, start=1):
        flake["id"] = f"flake_{i:05d}"

    return kept


def merge_jsons(args):
    tile_json_dir = Path(args.tile_json_dir)
    output_json = Path(args.output_json)

    offsets = parse_tile_configuration(args.tile_config)

    all_flakes = []
    missing_tiles = []

    json_files = [
        p for p in sorted(tile_json_dir.iterdir())
        if p.suffix.lower() == ".json" and not p.name.startswith("_")
    ]

    for json_path in json_files:
        with open(json_path, "r") as f:
            tile_data = json.load(f)

        tile_name = Path(tile_data["tile_name"]).name

        if tile_name not in offsets:
            missing_tiles.append(tile_name)
            continue

        x_offset = offsets[tile_name]["x_offset"]
        y_offset = offsets[tile_name]["y_offset"]

        for flake in tile_data["flakes"]:
            stitched = dict(flake)

            stitched["source_tile"] = tile_name
            stitched["tile_x"] = flake["x"]
            stitched["tile_y"] = flake["y"]

            stitched["x"] = round(flake["x"] + x_offset, 2)
            stitched["y"] = round(flake["y"] + y_offset, 2)

            stitched["bbox"] = {
                "x": int(round(flake["bbox"]["x"] + x_offset)),
                "y": int(round(flake["bbox"]["y"] + y_offset)),
                "width": flake["bbox"]["width"],
                "height": flake["bbox"]["height"],
            }

            stitched["polygon"] = [
                [round(px + x_offset, 2), round(py + y_offset, 2)]
                for px, py in flake["polygon"]
            ]

            all_flakes.append(stitched)

    before = len(all_flakes)

    if args.deduplicate:
        all_flakes = remove_duplicates(all_flakes, args.duplicate_distance)

    output = {
        "coordinate_system": "stitched_image_pixels",
        "flake_count": len(all_flakes),
        "flake_count_before_deduplication": before,
        "tile_config_file": str(args.tile_config),
        "missing_tiles_from_tile_config": missing_tiles,
        "flakes": all_flakes,
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)

    with open(output_json, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Flakes before duplicate removal: {before}")
    print(f"Final flakes: {len(all_flakes)}")
    print(f"Saved merged JSON to {output_json}")


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    detect = subparsers.add_parser("detect-folder")
    detect.add_argument("--tile-dir", required=True)
    detect.add_argument("--tile-json-dir", default="tile_json_rf")
    detect.add_argument("--preview-dir", default="tile_previews_rf")
    detect.add_argument("--model-id", default="grapheneflakes-72y6l-szuyj/2")
    detect.add_argument("--api-key", default=None)
    detect.add_argument("--confidence", type=float, default=0.35)
    detect.add_argument("--save-previews", action="store_true")

    merge = subparsers.add_parser("merge")
    merge.add_argument("--tile-json-dir", required=True)
    merge.add_argument("--tile-config", required=True)
    merge.add_argument("--output-json", default="public/flakes.json")
    merge.add_argument("--deduplicate", action="store_true")
    merge.add_argument("--duplicate-distance", type=float, default=50)

    args = parser.parse_args()

    if args.command == "detect-folder":
        run_detection_on_folder(args)
    elif args.command == "merge":
        merge_jsons(args)


if __name__ == "__main__":
    main()