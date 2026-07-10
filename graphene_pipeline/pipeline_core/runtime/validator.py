from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from config import FIJI_EXE, PATHS, WEBSITE
from pipeline_core.runtime.run_config import RunConfig


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.ok = False

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


def pattern_to_regex(pattern: str) -> re.Pattern:
    escaped = re.escape(pattern)
    escaped = escaped.replace(re.escape("{p}"), r"(?P<p>\d+)")
    return re.compile(f"^{escaped}$")


def validate_raw_folder(config: RunConfig, result: ValidationResult) -> None:
    if config.acquisition.enabled:
        raw_folder = Path(config.acquisition.output_folder or config.input.raw_folder or PATHS["raw_tiles"])
        if raw_folder.exists() and not raw_folder.is_dir():
            result.add_error(f"Acquisition output path is not a directory: {raw_folder}")
        if "{p}" not in config.input.raw_file_pattern:
            result.add_error("Raw file pattern must contain {p} when acquisition scanning is enabled.")
        return

    raw_folder = Path(config.input.raw_folder)

    if not raw_folder.exists():
        result.add_error(f"Raw folder does not exist: {raw_folder}")
        return

    if not raw_folder.is_dir():
        result.add_error(f"Raw folder is not a directory: {raw_folder}")
        return

    valid_exts = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}

    image_files = [
        p for p in raw_folder.iterdir()
        if p.is_file() and p.suffix.lower() in valid_exts
    ]

    if not image_files:
        result.add_error(f"No image files found in raw folder: {raw_folder}")
        return

    expected_count = config.stitching.grid_size_x * config.stitching.grid_size_y

    if len(image_files) != expected_count:
        result.add_warning(
            f"Image count does not match grid size. "
            f"Found {len(image_files)} images, expected {expected_count}."
        )

    if "{p}" not in config.input.raw_file_pattern:
        result.add_warning(
            "Raw file pattern does not contain {p}; tile numbering may not be detected."
        )
        return

    regex = pattern_to_regex(config.input.raw_file_pattern)
    matching = [p for p in image_files if regex.match(p.name)]

    if not matching:
        result.add_error(
            f"No files match raw file pattern: {config.input.raw_file_pattern}"
        )
    elif len(matching) != len(image_files):
        result.add_warning(
            f"Only {len(matching)} of {len(image_files)} images match raw file pattern."
        )


def validate_patterns(config: RunConfig, result: ValidationResult) -> None:
    if "{p}" not in config.input.corrected_file_pattern:
        result.add_error("Corrected file pattern must contain {p}.")

    if not config.input.corrected_file_pattern.lower().endswith((".tif", ".tiff")):
        result.add_warning("Corrected file pattern should usually end in .tif or .tiff.")


def validate_acquisition(config: RunConfig, result: ValidationResult) -> None:
    if not config.acquisition.enabled:
        return
    if not config.acquisition.serial_port:
        result.add_error("Acquisition serial_port is required when scan-chip is enabled.")
    if config.acquisition.baudrate <= 0:
        result.add_error("Acquisition baudrate must be positive.")
    if config.acquisition.step_x == 0 and config.stitching.grid_size_x > 1:
        result.add_error("Acquisition Tile FOV X Steps must be non-zero when grid_size_x is greater than 1.")
    if config.acquisition.step_y == 0 and config.stitching.grid_size_y > 1:
        result.add_error("Acquisition Tile FOV Y Steps must be non-zero when grid_size_y is greater than 1.")
    if config.acquisition.settle_seconds < 0:
        result.add_error("Acquisition settle_seconds cannot be negative.")
    if config.stitching.tile_overlap < 0 or config.stitching.tile_overlap >= 100:
        result.add_error("tile_overlap must be at least 0 and less than 100 for acquisition scanning.")


def validate_stitching(config: RunConfig, result: ValidationResult) -> None:
    if config.stitching.grid_size_x <= 0:
        result.add_error("grid_size_x must be greater than zero.")

    if config.stitching.grid_size_y <= 0:
        result.add_error("grid_size_y must be greater than zero.")

    if config.stitching.tile_overlap < 0:
        result.add_error("tile_overlap cannot be negative.")

    if not config.stitching.scan_order:
        result.add_error("scan_order cannot be empty.")


def validate_installation(result: ValidationResult) -> None:
    fiji = Path(FIJI_EXE).expanduser()

    if shutil.which(FIJI_EXE) is None and not fiji.exists():
        result.add_error(f"Fiji executable not found: {fiji}")

    website_public = Path(WEBSITE["public_dir"])

    if not website_public.exists():
        result.add_error(f"Website public directory not found: {website_public}")

    for key in ["raw_tiles", "corrected_tiles", "stitched", "exports", "dzi"]:
        path = PATHS[key]
        path.mkdir(parents=True, exist_ok=True)

        if not path.exists():
            result.add_error(f"Required path could not be created: {path}")


def validate_detection(result: ValidationResult) -> None:
    if not os.environ.get("ROBOFLOW_API_KEY"):
        result.add_warning(
            "ROBOFLOW_API_KEY is not set. Stage 3 will fail unless it is configured."
        )


def validate_run_config(config: RunConfig) -> ValidationResult:
    result = ValidationResult(ok=True)

    validate_raw_folder(config, result)
    validate_patterns(config, result)
    validate_stitching(config, result)
    validate_acquisition(config, result)
    validate_installation(result)
    validate_detection(result)

    return result


def print_validation_result(result: ValidationResult) -> None:
    print("=" * 70)
    print("Pipeline Validation")
    print("=" * 70)

    if result.errors:
        print("\nErrors:")
        for error in result.errors:
            print(f"  ERROR: {error}")

    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"  WARNING: {warning}")

    if result.ok:
        print("\nValidation passed.")
    else:
        print("\nValidation failed.")
