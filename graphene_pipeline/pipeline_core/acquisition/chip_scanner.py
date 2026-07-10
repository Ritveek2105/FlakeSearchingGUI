from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class RasterScanConfig:
    output_dir: Path
    file_pattern: str = "{p}.jpg"
    grid_size_x: int = 1
    grid_size_y: int = 1
    step_x: int = 0
    step_y: int = 0
    overlap_percent: float = 40.0
    settle_seconds: float = 0.5
    first_tile_index: int = 1
    serpentine: bool = True


@dataclass(frozen=True)
class TileRecord:
    tile_index: int
    row: int
    column: int
    x_steps: int
    y_steps: int
    path: str


def tile_name(pattern: str, tile_index: int) -> str:
    if "{p}" not in pattern:
        raise ValueError("Raw file pattern must contain {p} for acquisition scans.")
    return pattern.format(p=tile_index)


def effective_step(full_tile_steps: int, overlap_percent: float) -> int:
    if overlap_percent < 0 or overlap_percent >= 100:
        raise ValueError("overlap_percent must be at least 0 and less than 100.")
    if full_tile_steps == 0:
        return 0
    stride = round(abs(full_tile_steps) * (1.0 - overlap_percent / 100.0))
    stride = max(stride, 1)
    return stride if full_tile_steps > 0 else -stride


def generate_raster_positions(config: RasterScanConfig) -> list[tuple[int, int, int, int, int]]:
    if config.grid_size_x <= 0 or config.grid_size_y <= 0:
        raise ValueError("grid_size_x and grid_size_y must be positive.")

    step_x = effective_step(config.step_x, config.overlap_percent)
    step_y = effective_step(config.step_y, config.overlap_percent)

    positions: list[tuple[int, int, int, int, int]] = []
    tile_index = config.first_tile_index

    for row in range(config.grid_size_y):
        columns = range(config.grid_size_x)
        if config.serpentine and row % 2 == 1:
            columns = reversed(range(config.grid_size_x))

        for column in columns:
            x_steps = column * step_x
            y_steps = row * step_y
            positions.append((tile_index, row, column, x_steps, y_steps))
            tile_index += 1

    return positions


class ChipScanner:
    """Raster-scan a chip and save camera frames as pipeline raw tiles."""

    def __init__(self, stage, camera) -> None:
        self.stage = stage
        self.camera = camera

    def run(self, config: RasterScanConfig) -> list[TileRecord]:
        config.output_dir.mkdir(parents=True, exist_ok=True)
        positions = generate_raster_positions(config)
        records: list[TileRecord] = []
        current_x = 0
        current_y = 0

        for tile_index, row, column, target_x, target_y in positions:
            dx = target_x - current_x
            dy = target_y - current_y
            if dx:
                self.stage.move_relative("X", dx)
            if dy:
                self.stage.move_relative("Y", dy)
            current_x = target_x
            current_y = target_y

            time.sleep(config.settle_seconds)
            output_path = config.output_dir / tile_name(config.file_pattern, tile_index)
            self.camera.save_frame(output_path)
            records.append(
                TileRecord(
                    tile_index=tile_index,
                    row=row,
                    column=column,
                    x_steps=target_x,
                    y_steps=target_y,
                    path=str(output_path),
                )
            )

        manifest_path = config.output_dir / "scan_manifest.json"
        manifest = {
            "config": {**asdict(config), "output_dir": str(config.output_dir)},
            "tiles": [asdict(record) for record in records],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        return records

