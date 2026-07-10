import json
import shutil
import sys
from datetime import datetime
from pathlib import Path


from config import PROJECT_DIR

PROJECT_ROOT = PROJECT_DIR


from config import PATHS, IMAGE, JSON_MERGE, PUBLISH_SAMPLE, WEBSITE


def load_json(path: Path, default):
    if not path.exists():
        return default

    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_next_sample_id(samples_dir: Path, prefix: str) -> str:
    samples_dir.mkdir(parents=True, exist_ok=True)

    max_number = 0

    for item in samples_dir.iterdir():
        if not item.is_dir():
            continue

        name = item.name

        if not name.startswith(prefix + "_"):
            continue

        try:
            number = int(name.split("_")[-1])
            max_number = max(max_number, number)
        except ValueError:
            continue

    return f"{prefix}_{max_number + 1:06d}"


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


def get_flake_count(flakes_json_path: Path) -> int | None:
    if not flakes_json_path.exists():
        return None

    data = load_json(flakes_json_path, {})

    if isinstance(data, dict):
        if "flakes" in data and isinstance(data["flakes"], list):
            return len(data["flakes"])

        metadata = data.get("metadata")
        if isinstance(metadata, dict):
            count = metadata.get("detection_count")
            if isinstance(count, int):
                return count

    return None


def update_samples_catalog(catalog_path: Path, sample_id: str, sample_web_path: str) -> None:
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
        sample for sample in samples
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


def main() -> None:
    print("=" * 70)
    print("Stage 5: Publish Sample to Website")
    print("=" * 70)

    website_public = Path(WEBSITE["public_dir"])
    samples_root = website_public / "samples"

    sample_id = get_next_sample_id(
        samples_dir=samples_root,
        prefix=PUBLISH_SAMPLE["sample_prefix"],
    )

    sample_dir = samples_root / sample_id
    sample_web_path = f"/samples/{sample_id}"

    print(f"Publishing sample:")
    print(f"  {sample_id}")
    print(f"Destination:")
    print(f"  {sample_dir}")

    dzi_src = PATHS["dzi"] / PUBLISH_SAMPLE["dzi_source_name"]
    dzi_files_src = PATHS["dzi"] / PUBLISH_SAMPLE["dzi_files_source_name"]

    flakes_src = PATHS["exports"] / JSON_MERGE["final_json_name"]

    preview_src = PATHS["tile_previews"] / PUBLISH_SAMPLE["preview_source_name"]

    dzi_dst = sample_dir / PUBLISH_SAMPLE["published_dzi_name"]
    dzi_files_dst = sample_dir / PUBLISH_SAMPLE["published_dzi_files_name"]
    flakes_dst = sample_dir / "flakes.json"
    preview_dst = sample_dir / PUBLISH_SAMPLE["published_preview_name"]
    metadata_dst = sample_dir / PUBLISH_SAMPLE["metadata_name"]

    print("Copying DZI...")
    copy_file_required(dzi_src, dzi_dst)

    print("Copying DZI tile folder...")
    copy_dir_required(dzi_files_src, dzi_files_dst)

    print("Copying flakes.json...")
    copy_file_required(flakes_src, flakes_dst)

    print("Copying preview...")
    copy_file_required(preview_src, preview_dst)

    flake_count = get_flake_count(flakes_src)

    metadata = {
        "id": sample_id,
        "name": sample_id.replace("_", " ").title(),
        "published_at": datetime.now().isoformat(timespec="seconds"),
        "scan_date": "",
        "objective": IMAGE.get("objective", ""),
        "camera": IMAGE.get("camera", ""),
        "sample_type": IMAGE.get("sample_type", ""),
        "operator": "Jason Zheng",
        "flake_count": flake_count,
        "image_width": None,
        "image_height": None,
        "notes": "Published from graphene pipeline Stage 5.",
    }

    print("Writing metadata.json...")
    save_json(metadata_dst, metadata)

    catalog_path = website_public / PUBLISH_SAMPLE["samples_catalog_name"]

    print("Updating samples.json...")
    update_samples_catalog(
        catalog_path=catalog_path,
        sample_id=sample_id,
        sample_web_path=sample_web_path,
    )

    print("=" * 70)
    print("Stage 5 complete")
    print("=" * 70)
    print(f"Published sample:")
    print(f"  {sample_id}")
    print(f"Website folder:")
    print(f"  {sample_dir}")
    print(f"Refresh your website to see the new sample.")


if __name__ == "__main__":
    main()
