from pathlib import Path

from pipeline_core.runtime.validator import pattern_to_regex
from pipeline_core.runtime.run_config import (
    RunConfig,
    InputConfig,
    StitchingConfig,
)
from pipeline_core.runtime.validator import validate_run_config


def test_pattern_matches_simple_numbered_jpg():
    regex = pattern_to_regex("{p}.jpg")

    assert regex.match("1.jpg")
    assert regex.match("25.jpg")
    assert not regex.match("tile_1.jpg")


def test_pattern_matches_graphene_numbered_jpg():
    regex = pattern_to_regex("{p}_graphene.jpg")

    assert regex.match("1_graphene.jpg")
    assert regex.match("36_graphene.jpg")
    assert not regex.match("1.jpg")


def test_pattern_matches_prefixed_tile_name():
    regex = pattern_to_regex("tile_{p}.tif")

    assert regex.match("tile_1.tif")
    assert regex.match("tile_12.tif")
    assert not regex.match("1_tile.tif")


def test_validator_accepts_matching_raw_files(tmp_path: Path):
    raw_dir = tmp_path / "raw_tiles"
    raw_dir.mkdir()

    for i in range(1, 4):
        (raw_dir / f"{i}.jpg").write_bytes(b"fake image data")

    config = RunConfig(
        input=InputConfig(
            raw_folder=str(raw_dir),
            raw_file_pattern="{p}.jpg",
            corrected_file_pattern="{p}_corrected.tif",
        ),
        stitching=StitchingConfig(
            grid_size_x=3,
            grid_size_y=1,
            tile_overlap=40,
            scan_order="HORIZONTALCONTINUOUS",
            first_tile_index=1,
        ),
    )

    result = validate_run_config(config)

    raw_pattern_errors = [
        e for e in result.errors
        if "No files match raw file pattern" in e
    ]

    assert not raw_pattern_errors


def test_validator_warns_when_grid_count_mismatch(tmp_path: Path):
    raw_dir = tmp_path / "raw_tiles"
    raw_dir.mkdir()

    for i in range(1, 3):
        (raw_dir / f"{i}.jpg").write_bytes(b"fake image data")

    config = RunConfig(
        input=InputConfig(
            raw_folder=str(raw_dir),
            raw_file_pattern="{p}.jpg",
            corrected_file_pattern="{p}_corrected.tif",
        ),
        stitching=StitchingConfig(
            grid_size_x=3,
            grid_size_y=1,
            tile_overlap=40,
            scan_order="HORIZONTALCONTINUOUS",
            first_tile_index=1,
        ),
    )

    result = validate_run_config(config)

    mismatch_warnings = [
        w for w in result.warnings
        if "Image count does not match grid size" in w
    ]

    assert mismatch_warnings