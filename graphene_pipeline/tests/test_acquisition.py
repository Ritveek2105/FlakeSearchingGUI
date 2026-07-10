from pathlib import Path

import numpy as np

from pipeline_core.acquisition.amscope_camera import AmScopeCamera
from pipeline_core.acquisition.chip_scanner import RasterScanConfig, effective_step, generate_raster_positions, tile_name
from pipeline_core.acquisition.serial_stage import StepPosition, parse_arduino_line


def test_parse_arduino_line_accepts_labeled_position():
    assert parse_arduino_line("POS,100,200,-30") == StepPosition(100, 200, -30)


def test_parse_arduino_line_accepts_plain_position():
    assert parse_arduino_line("100,200,300") == StepPosition(100, 200, 300)


def test_parse_arduino_line_ignores_non_position_text():
    assert parse_arduino_line("ready") is None


def test_generate_raster_positions_serpentine():
    config = RasterScanConfig(
        output_dir=Path("raw"),
        grid_size_x=3,
        grid_size_y=2,
        step_x=10,
        step_y=20,
        first_tile_index=1,
        serpentine=True,
        overlap_percent=0,
    )

    assert generate_raster_positions(config) == [
        (1, 0, 0, 0, 0),
        (2, 0, 1, 10, 0),
        (3, 0, 2, 20, 0),
        (4, 1, 2, 20, 20),
        (5, 1, 1, 10, 20),
        (6, 1, 0, 0, 20),
    ]


def test_tile_name_requires_number_placeholder():
    assert tile_name("{p}_graphene.jpg", 7) == "7_graphene.jpg"


def test_effective_step_applies_overlap_percent():
    assert effective_step(100, 40) == 60
    assert effective_step(-100, 40) == -60


def test_decode_padded_camera_frame_crops_stride_padding():
    width = 3
    height = 2
    stride = AmScopeCamera._stride_bytes(width)
    assert stride == 12

    rows = []
    for row in range(height):
        pixels = np.arange(row * width * 3, (row + 1) * width * 3, dtype=np.uint8)
        padding = np.array([250, 251, 252], dtype=np.uint8)
        rows.append(np.concatenate([pixels, padding]))

    buffer = np.concatenate(rows).tobytes()
    frame = AmScopeCamera._decode_padded_frame(buffer, width, height)

    assert frame.shape == (height, width, 3)
    assert frame[0, 0].tolist() == [0, 1, 2]
    assert frame[1, 2].tolist() == [15, 16, 17]
