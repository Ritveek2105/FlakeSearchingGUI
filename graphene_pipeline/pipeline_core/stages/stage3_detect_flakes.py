import argparse
import shutil
import sys
from pathlib import Path


# =====================================================
# Project bootstrap
# =====================================================

from config import PROJECT_DIR

PROJECT_ROOT = PROJECT_DIR


# =====================================================
# Project imports
# =====================================================

from config import PATHS, STITCHED_ANALYSIS, ROBOFLOW, JSON_MERGE

from pipeline_core.runtime.run_config import RunConfig, load_run_config

from pipeline_core.detection.tiling import (
    load_rgb_image,
    generate_tiles,
    save_tile_png,
)

from pipeline_core.detection.roboflow_client import (
    run_roboflow_inference,
    convert_predictions_to_global,
)

from pipeline_core.detection.merge import merge_duplicate_detections
from pipeline_core.detection.export import save_tile_json, save_flakes_json
from pipeline_core.detection.visualization import save_detection_preview


# =====================================================
# Helpers
# =====================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 3: Roboflow flake detection.")
    parser.add_argument(
        "--run-config",
        type=Path,
        default=None,
        help="Optional runtime config path.",
    )
    return parser.parse_args()


def clear_folder(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)

    for item in folder.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)


def get_detection_settings(run_config: RunConfig) -> dict:
    """
    Runtime config takes priority.
    config.py remains the fallback for direct standalone execution.
    """
    model_id = (
        run_config.detection.roboflow_model_id
        or ROBOFLOW["model_id"]
    )

    confidence = (
        run_config.detection.roboflow_confidence
        if run_config.detection.roboflow_confidence is not None
        else float(ROBOFLOW["confidence"])
    )

    tile_size = (
        run_config.detection.tile_size
        if run_config.detection.tile_size is not None
        else int(ROBOFLOW["tile_size"])
    )

    tile_overlap = (
        run_config.detection.tile_overlap
        if run_config.detection.tile_overlap is not None
        else int(ROBOFLOW["tile_overlap"])
    )

    api_url = ROBOFLOW["api_url"]
    save_tile_images = bool(ROBOFLOW.get("save_tile_images", True))

    return {
        "model_id": model_id,
        "confidence": float(confidence),
        "tile_size": int(tile_size),
        "tile_overlap": int(tile_overlap),
        "api_url": api_url,
        "save_tile_images": save_tile_images,
    }


# =====================================================
# Main
# =====================================================

def main() -> None:
    args = parse_args()
    run_config = load_run_config(args.run_config) if args.run_config else RunConfig()

    print("=" * 70)
    print("Stage 3: Roboflow Flake Detection")
    print("=" * 70)

    stitched_dir = PATHS["stitched"]
    tile_json_dir = PATHS["tile_json"]
    tile_preview_dir = PATHS["tile_previews"]
    export_dir = PATHS["exports"]

    clear_folder(tile_json_dir)
    clear_folder(tile_preview_dir)

    input_name = STITCHED_ANALYSIS["output_corrected_name"]
    input_path = stitched_dir / input_name

    if not input_path.exists():
        raise FileNotFoundError(
            f"Could not find corrected stitched image:\n{input_path}\n\n"
            "Stage 3 expects Stage 2 output: Fused_corrected.tif"
        )

    print("Loading corrected stitched image:")
    print(f"  {input_path}")

    image = load_rgb_image(input_path)
    image_height, image_width = image.shape[:2]

    print("Image size:")
    print(f"  width:  {image_width}")
    print(f"  height: {image_height}")

    settings = get_detection_settings(run_config)

    tile_size = settings["tile_size"]
    overlap = settings["tile_overlap"]
    confidence = settings["confidence"]
    model_id = settings["model_id"]
    api_url = settings["api_url"]
    save_tile_images = settings["save_tile_images"]

    print("Detection settings:")
    print(f"  model_id:   {model_id}")
    print(f"  confidence: {confidence}")
    print(f"  tile_size:  {tile_size}")
    print(f"  overlap:    {overlap}")

    all_detections = []

    tiles = list(
        generate_tiles(
            image=image,
            tile_size=tile_size,
            overlap=overlap,
        )
    )

    print(f"Generated {len(tiles)} inference tiles.")

    for index, tile in enumerate(tiles, start=1):
        print("-" * 70)
        print(f"Processing {tile.tile_id} ({index}/{len(tiles)})")
        print(f"  origin: x={tile.x0}, y={tile.y0}")
        print(f"  size:   {tile.width} x {tile.height}")

        # Currently Roboflow inference requires a saved image file.
        # save_tile_images controls whether these are considered debug artifacts,
        # but the tile still has to be written for inference.
        tile_image_path = save_tile_png(tile, tile_preview_dir)

        result = run_roboflow_inference(
            image_path=tile_image_path,
            model_id=model_id,
            confidence=confidence,
            api_url=api_url,
        )

        save_tile_json(
            result=result,
            tile_id=tile.tile_id,
            output_dir=tile_json_dir,
        )

        tile_detections = convert_predictions_to_global(
            roboflow_result=result,
            tile_id=tile.tile_id,
            tile_x0=tile.x0,
            tile_y0=tile.y0,
        )

        print(f"  detections: {len(tile_detections)}")

        all_detections.extend(tile_detections)

    print("=" * 70)
    print("Merging detections")
    print("=" * 70)

    print(f"Raw detections before merge: {len(all_detections)}")

    if JSON_MERGE.get("deduplicate", True):
        detections = merge_duplicate_detections(
            detections=all_detections,
            duplicate_distance_px=float(JSON_MERGE["duplicate_distance_px"]),
        )
    else:
        detections = all_detections
        for i, det in enumerate(detections, start=1):
            det["id"] = i

    print(f"Final detections after merge: {len(detections)}")

    flakes_json_path = export_dir / JSON_MERGE["final_json_name"]

    save_flakes_json(
        detections=detections,
        output_path=flakes_json_path,
        image_name=input_name,
        image_width=image_width,
        image_height=image_height,
        model_id=model_id,
    )

    preview_path = tile_preview_dir / "stage3_detection_preview.png"

    save_detection_preview(
        image=image,
        detections=detections,
        output_path=preview_path,
    )

    print("=" * 70)
    print("Stage 3 complete")
    print("=" * 70)
    print("Saved final detections:")
    print(f"  {flakes_json_path}")
    print("Saved preview:")
    print(f"  {preview_path}")


if __name__ == "__main__":
    main()
