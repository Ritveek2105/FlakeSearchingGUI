import argparse
import json
import shutil
import sys
from pathlib import Path

from PIL import Image


# =====================================================
# Project bootstrap
# =====================================================

from config import PROJECT_DIR

PROJECT_ROOT = PROJECT_DIR


# =====================================================
# Project imports
# =====================================================

from config import (
    PATHS,
    JSON_MERGE,
    GENERATE_DZI,
    PUBLISH_SAMPLE,
    STITCHED_ANALYSIS,
    WEBSITE,
)

from pipeline_core.runtime.run_config import RunConfig, load_run_config
from pipeline_core.runtime.sample_metadata import build_sample_metadata


Image.MAX_IMAGE_PIXELS = None


# =====================================================
# JSON helpers
# =====================================================

def load_json(path: Path, default):
    if not path.exists():
        return default

    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def create_empty_flakes_json(path: Path) -> None:
    """
    Creates an empty flakes.json for manual annotation mode.
    """

    save_json(
        path,
        {
            "source": "manual",
            "flakes": [],
        },
    )


def create_empty_annotations_json(path: Path) -> None:
    """
    Creates an empty annotations.json for website manual bounding-box annotation.

    Existing annotations should not be overwritten during republish.
    """

    if path.exists():
        print("annotations.json already exists; preserving existing manual annotations.")
        return

    save_json(
        path,
        {
            "version": 1,
            "boxes": [],
        },
    )

# =====================================================
# File helpers
# =====================================================

def copy_file_required(src: Path, dst: Path) -> None:
    if not src.exists():
        raise FileNotFoundError(f"Missing required file:\n{src}")

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def copy_dir_required(src: Path, dst: Path) -> None:
    if not src.exists():
        raise FileNotFoundError(f"Missing required folder:\n{src}")

    if dst.exists():
        shutil.rmtree(dst)

    shutil.copytree(src, dst)


def resolve_preview_source() -> Path:
    candidates = [
        PATHS["tile_previews"] / "stage3_detection_preview.png",
        PATHS["data"] / "stage2_outputs" / STITCHED_ANALYSIS["corrected_preview_name"],
        PATHS["data"] / "stage2_outputs" / STITCHED_ANALYSIS["preview_name"],
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    attempted = "\n".join(str(path) for path in candidates)
    raise FileNotFoundError(
        "Missing preview image. Tried:\n"
        f"{attempted}\n\n"
        "Manual detection mode skips Stage 3, so Stage 6 expects a Stage 2 "
        "preview if no detection preview exists."
    )


# =====================================================
# Sample/catalog helpers
# =====================================================

def get_next_sample_id(samples_dir: Path, prefix: str) -> str:
    samples_dir.mkdir(parents=True, exist_ok=True)

    max_number = 0

    for item in samples_dir.iterdir():
        if not item.is_dir():
            continue

        if not item.name.startswith(prefix + "_"):
            continue

        try:
            number = int(item.name.split("_")[-1])
            max_number = max(max_number, number)
        except ValueError:
            continue

    return f"{prefix}_{max_number + 1:06d}"


def resolve_sample_id(
    samples_root: Path,
    run_config: RunConfig,
    cli_sample: str | None,
) -> tuple[str, str]:
    """
    Returns:
        sample_id, publish_mode

    Supported modes:
        new
        republish
        preview
    """
    if cli_sample:
        return cli_sample, "republish"

    mode = run_config.publish.mode.lower().strip()

    if mode == "republish":
        if not run_config.publish.sample_id:
            raise ValueError(
                "Publish mode is 'republish', but no sample_id was provided."
            )
        return run_config.publish.sample_id, "republish"

    if mode == "preview":
        return "preview", "preview"

    sample_id = get_next_sample_id(
        samples_dir=samples_root,
        prefix=PUBLISH_SAMPLE["sample_prefix"],
    )

    return sample_id, "new"


def update_samples_catalog(
    catalog_path: Path,
    sample_id: str,
    sample_web_path: str,
    publish_mode: str,
) -> None:
    """
    Update website public/samples.json.

    Preview samples are intentionally not added to the catalog.
    """
    if publish_mode == "preview":
        print("Preview mode: samples.json will not be updated.")
        return

    catalog = load_json(
        catalog_path,
        {
            "version": 1,
            "samples": [],
        },
    )

    if isinstance(catalog, list):
        catalog = {
            "version": 1,
            "samples": catalog,
        }

    samples = catalog.setdefault("samples", [])

    samples = [
        sample
        for sample in samples
        if sample.get("id") != sample_id
    ]

    samples.append(
        {
            "id": sample_id,
            "path": sample_web_path,
        }
    )

    catalog["samples"] = samples

    save_json(catalog_path, catalog)


# =====================================================
# Data helpers
# =====================================================

def get_flake_count(flakes_json_path: Path) -> int | None:
    data = load_json(flakes_json_path, {})

    if isinstance(data, dict):
        flakes = data.get("flakes")
        if isinstance(flakes, list):
            return len(flakes)

        metadata = data.get("metadata")
        if isinstance(metadata, dict):
            count = metadata.get("detection_count")
            if isinstance(count, int):
                return count

    return None


def get_image_size(image_path: Path) -> tuple[int | None, int | None]:
    if not image_path.exists():
        return None, None

    with Image.open(image_path) as img:
        return img.size


# =====================================================
# Main
# =====================================================

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Stage 6: publish processed sample to website."
    )

    parser.add_argument(
        "--sample",
        type=str,
        default=None,
        help="Existing sample ID to republish, for example graphene_000002.",
    )

    parser.add_argument(
        "--run-config",
        type=Path,
        default=None,
        help="Runtime config path.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_config = load_run_config(args.run_config) if args.run_config else RunConfig()

    print("=" * 70)
    print("Stage 6: Publish Sample to Website")
    print("=" * 70)

    website_public = Path(WEBSITE["public_dir"])
    samples_root = website_public / "samples"

    sample_id, publish_mode = resolve_sample_id(
        samples_root=samples_root,
        run_config=run_config,
        cli_sample=args.sample,
    )

    sample_dir = samples_root / sample_id
    sample_web_path = f"/samples/{sample_id}"

    print(f"Publish mode:")
    print(f"  {publish_mode}")
    print(f"Sample ID:")
    print(f"  {sample_id}")
    print(f"Destination:")
    print(f"  {sample_dir}")

    dzi_basename = GENERATE_DZI["dzi_basename"]

    dzi_src = PATHS["dzi"] / f"{dzi_basename}.dzi"
    dzi_files_src = PATHS["dzi"] / f"{dzi_basename}_files"

    flakes_src = PATHS["exports"] / JSON_MERGE["final_json_name"]
    preview_src = resolve_preview_source()
    image_src = PATHS["stitched"] / GENERATE_DZI["input_image_name"]

    dzi_dst = sample_dir / PUBLISH_SAMPLE["published_dzi_name"]
    dzi_files_dst = sample_dir / PUBLISH_SAMPLE["published_dzi_files_name"]
    flakes_dst = sample_dir / "flakes.json"
    annotations_dst = sample_dir / "annotations.json"
    preview_dst = sample_dir / PUBLISH_SAMPLE["published_preview_name"]
    metadata_dst = sample_dir / PUBLISH_SAMPLE["metadata_name"]
    source_image_dst = sample_dir / "source.tif"

    print("Copying DZI...")
    copy_file_required(dzi_src, dzi_dst)

    print("Copying DZI tile folder...")
    copy_dir_required(dzi_files_src, dzi_files_dst)

    print("Copying full source stitched image for dataset export...")
    copy_file_required(image_src, source_image_dst)

    print("Ensuring annotations.json exists...")
    create_empty_annotations_json(annotations_dst)

    if run_config.detection.mode.lower() == "manual":

        print("Creating empty flakes.json for manual annotation...")

        create_empty_flakes_json(flakes_dst)

    else:

        print("Copying flakes.json...")

        copy_file_required(flakes_src, flakes_dst)

    print("Copying preview...")
    copy_file_required(preview_src, preview_dst)

    if run_config.detection.mode.lower() == "manual":
        flake_count = 0
    else:
        flake_count = get_flake_count(flakes_src)

    image_width, image_height = get_image_size(image_src)

    metadata = build_sample_metadata(
        sample_id=sample_id,
        run_config=run_config,
        source_image="source.tif",
        image_width=image_width,
        image_height=image_height,
        flake_count=flake_count,
    )

    print("Writing metadata.json...")
    save_json(metadata_dst, metadata.to_dict())

    catalog_path = website_public / PUBLISH_SAMPLE["samples_catalog_name"]

    print("Updating samples.json...")
    update_samples_catalog(
        catalog_path=catalog_path,
        sample_id=sample_id,
        sample_web_path=sample_web_path,
        publish_mode=publish_mode,
    )

    print("=" * 70)
    print("Stage 6 complete")
    print("=" * 70)
    print(f"Published sample:")
    print(f"  {sample_id}")
    print(f"Website folder:")
    print(f"  {sample_dir}")
    print(f"Source image saved:")
    print(f"  {source_image_dst}")

    if publish_mode == "preview":
        print("Preview mode was used, so the sample was not added to samples.json.")
    else:
        print("Refresh your website to see the new or updated sample.")


if __name__ == "__main__":
    main()
