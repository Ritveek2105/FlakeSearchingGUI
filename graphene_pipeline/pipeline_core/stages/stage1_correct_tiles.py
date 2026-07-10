from pathlib import Path
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import os
import re
import shutil
import sys
import time


from config import PROJECT_DIR

PROJECT_ROOT = PROJECT_DIR


from config import PATHS
from pipeline_core.runtime.run_config import RunConfig, load_run_config
from pipeline_core.illumination.tile_correction import (
    MASK_OUTPUT_FOLDER,
    OUTPUT_FOLDER,
    POINTS_OUTPUT_FOLDER,
    INPUT_FOLDER,
    ensure_output_folders,
    get_image_paths,
    process_tile,
)
from pipeline_core.utils.logger import PipelineLogger
from pipeline_core.utils.report import StageReport


def clear_folder(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)

    for item in folder.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)


def pattern_to_regex(pattern: str) -> re.Pattern:
    """
    Convert a naming pattern like:
        {p}_graphene.jpg
        tile_{p}.tif

    into a regex that extracts the tile number.
    """
    escaped = re.escape(pattern)
    escaped = escaped.replace(re.escape("{p}"), r"(?P<p>\d+)")
    return re.compile(f"^{escaped}$")


def extract_tile_number(filename: str, pattern: str, fallback: int) -> int:
    regex = pattern_to_regex(pattern)
    match = regex.match(filename)

    if match:
        return int(match.group("p"))

    return fallback


def rename_outputs_for_pattern(
    image_path: Path,
    tile_number: int,
    run_config: RunConfig,
) -> None:
    """
    The existing tile_correction library writes files based on the raw filename stem.
    This wrapper renames the corrected TIFF to the runtime-configured corrected pattern.

    Example:
        raw: sampleA_001.jpg
        corrected pattern: {p}_graphene_corrected.tif
        output: 1_graphene_corrected.tif
    """

    raw_stem = image_path.stem

    original_corrected = OUTPUT_FOLDER / f"{raw_stem}_corrected.tif"
    original_mask = MASK_OUTPUT_FOLDER / f"{raw_stem}_flake_mask.png"
    original_points = POINTS_OUTPUT_FOLDER / f"{raw_stem}_bare_points.png"

    corrected_name = run_config.input.corrected_file_pattern.replace(
        "{p}", str(tile_number)
    )

    corrected_target = OUTPUT_FOLDER / corrected_name
    target_stem = corrected_target.stem

    mask_target = MASK_OUTPUT_FOLDER / f"{target_stem}_flake_mask.png"
    points_target = POINTS_OUTPUT_FOLDER / f"{target_stem}_bare_points.png"

    rename_if_needed(original_corrected, corrected_target)
    rename_if_needed(original_mask, mask_target)
    rename_if_needed(original_points, points_target)


def rename_if_needed(src: Path, dst: Path) -> None:
    if not src.exists():
        return

    if src.resolve() == dst.resolve():
        return

    if dst.exists():
        dst.unlink()

    src.rename(dst)


def resolve_worker_count(tile_count: int) -> int:
    if tile_count <= 1:
        return 1

    requested = os.environ.get("GRAPHENE_STAGE1_WORKERS")

    if requested:
        try:
            worker_count = int(requested)
        except ValueError as exc:
            raise ValueError("GRAPHENE_STAGE1_WORKERS must be a positive integer.") from exc
    else:
        worker_count = min(4, os.cpu_count() or 1)

    return max(1, min(worker_count, tile_count))


def process_tile_entry(entry: tuple[int, Path]) -> tuple[int, Path, bool]:
    tile_number, image_path = entry
    return tile_number, image_path, process_tile(image_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-config", type=Path, default=None)
    args = parser.parse_args()

    run_config = load_run_config(args.run_config) if args.run_config else RunConfig()

    logger = PipelineLogger(PROJECT_ROOT / "logs")
    report = StageReport(PATHS["reports"], "stage1_correct_tiles")

    logger.info("Stage 1 started: individual tile illumination correction")
    logger.info("Using runtime-aware Stage 1 wrapper")
    logger.info(f"Raw file pattern: {run_config.input.raw_file_pattern}")
    logger.info(f"Corrected file pattern: {run_config.input.corrected_file_pattern}")

    start = time.time()

    try:
        ensure_output_folders()

        clear_folder(OUTPUT_FOLDER)
        clear_folder(MASK_OUTPUT_FOLDER)
        clear_folder(POINTS_OUTPUT_FOLDER)

        image_paths = get_image_paths()

        first_tile = run_config.stitching.first_tile_index
        tile_entries = []

        for fallback_index, image_path in enumerate(image_paths, start=first_tile):
            tile_number = extract_tile_number(
                filename=image_path.name,
                pattern=run_config.input.raw_file_pattern,
                fallback=fallback_index,
            )
            tile_entries.append((tile_number, image_path))

        processed_count = 0
        skipped_count = 0
        worker_count = resolve_worker_count(len(tile_entries))
        logger.info(f"Stage 1 worker count: {worker_count}")

        if worker_count == 1:
            results = [process_tile_entry(entry) for entry in tile_entries]
        else:
            results = []
            with ProcessPoolExecutor(max_workers=worker_count) as executor:
                futures = [
                    executor.submit(process_tile_entry, entry)
                    for entry in tile_entries
                ]

                for future in as_completed(futures):
                    results.append(future.result())

        for tile_number, image_path, was_processed in sorted(results):
            if not was_processed:
                skipped_count += 1
                continue

            processed_count += 1
            rename_outputs_for_pattern(
                image_path=image_path,
                tile_number=tile_number,
                run_config=run_config,
            )

        elapsed = time.time() - start

        raw_count = len(list(INPUT_FOLDER.glob("*")))
        corrected_count = len(list(OUTPUT_FOLDER.glob("*.tif")))
        mask_count = len(list(MASK_OUTPUT_FOLDER.glob("*.png")))
        points_count = len(list(POINTS_OUTPUT_FOLDER.glob("*.png")))

        logger.info(f"Stage 1 completed successfully in {elapsed:.2f} seconds")
        logger.info(f"Raw tile count: {raw_count}")
        logger.info(f"Processed tile count: {processed_count}")
        logger.info(f"Skipped tile count: {skipped_count}")
        logger.info(f"Corrected tile count: {corrected_count}")
        logger.info(f"Mask count: {mask_count}")
        logger.info(f"Bare-chip preview count: {points_count}")

        report.success(
            elapsed_seconds=round(elapsed, 2),
            raw_tile_count=raw_count,
            processed_tile_count=processed_count,
            skipped_tile_count=skipped_count,
            corrected_tile_count=corrected_count,
            flake_mask_count=mask_count,
            bare_chip_preview_count=points_count,
            raw_file_pattern=run_config.input.raw_file_pattern,
            corrected_file_pattern=run_config.input.corrected_file_pattern,
            worker_count=worker_count,
            output_corrected_dir=str(OUTPUT_FOLDER),
            output_mask_dir=str(MASK_OUTPUT_FOLDER),
            output_points_dir=str(POINTS_OUTPUT_FOLDER),
        )

    except Exception as e:
        elapsed = time.time() - start
        logger.error(f"Stage 1 failed after {elapsed:.2f} seconds: {e}")
        report.failure(
            error=str(e),
            elapsed_seconds=round(elapsed, 2),
        )
        raise


if __name__ == "__main__":
    main()
