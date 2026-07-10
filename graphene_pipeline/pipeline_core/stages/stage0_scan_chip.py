from __future__ import annotations

import argparse
from pathlib import Path

from config import PATHS
from pipeline_core.acquisition.amscope_camera import AmScopeCamera
from pipeline_core.acquisition.chip_scanner import ChipScanner, RasterScanConfig
from pipeline_core.acquisition.serial_stage import ArduinoStageController
from pipeline_core.runtime.run_config import load_run_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan a graphene chip into raw tile images.")
    parser.add_argument("--run-config", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=PATHS["raw_tiles"])
    parser.add_argument("--file-pattern", default="{p}.jpg")
    parser.add_argument("--grid-size-x", type=int, default=1)
    parser.add_argument("--grid-size-y", type=int, default=1)
    parser.add_argument("--first-tile-index", type=int, default=1)
    parser.add_argument("--step-x", type=int, default=0, help="Camera field-of-view width in motor steps before overlap.")
    parser.add_argument("--step-y", type=int, default=0, help="Camera field-of-view height in motor steps before overlap.")
    parser.add_argument("--overlap-percent", type=float, default=40.0)
    parser.add_argument("--settle-seconds", type=float, default=0.5)
    parser.add_argument("--serial-port", default="COM3")
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--no-serpentine", action="store_true")
    return parser


def config_from_args(args: argparse.Namespace) -> RasterScanConfig:
    if args.run_config:
        run_config = load_run_config(args.run_config)
        acquisition = run_config.acquisition
        return RasterScanConfig(
            output_dir=Path(acquisition.output_folder or run_config.input.raw_folder or PATHS["raw_tiles"]),
            file_pattern=run_config.input.raw_file_pattern,
            grid_size_x=run_config.stitching.grid_size_x,
            grid_size_y=run_config.stitching.grid_size_y,
            step_x=acquisition.step_x,
            step_y=acquisition.step_y,
            overlap_percent=run_config.stitching.tile_overlap,
            settle_seconds=acquisition.settle_seconds,
            first_tile_index=run_config.stitching.first_tile_index,
            serpentine=acquisition.serpentine,
        )

    return RasterScanConfig(
        output_dir=args.output_dir,
        file_pattern=args.file_pattern,
        grid_size_x=args.grid_size_x,
        grid_size_y=args.grid_size_y,
        step_x=args.step_x,
        step_y=args.step_y,
        overlap_percent=args.overlap_percent,
        settle_seconds=args.settle_seconds,
        first_tile_index=args.first_tile_index,
        serpentine=not args.no_serpentine,
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    scan_config = config_from_args(args)

    serial_port = args.serial_port
    baudrate = args.baudrate
    if args.run_config:
        run_config = load_run_config(args.run_config)
        serial_port = run_config.acquisition.serial_port
        baudrate = run_config.acquisition.baudrate

    print("=" * 80)
    print("Stage 0: Chip Acquisition Scan")
    print("=" * 80)
    print(f"Output folder: {scan_config.output_dir}")
    print(f"Grid: {scan_config.grid_size_x} x {scan_config.grid_size_y}")
    print(f"Field-of-view X/Y steps: {scan_config.step_x}, {scan_config.step_y}")
    print(f"Overlap: {scan_config.overlap_percent}%")

    with ArduinoStageController(port=serial_port, baudrate=baudrate) as stage:
        with AmScopeCamera() as camera:
            records = ChipScanner(stage, camera).run(scan_config)

    print(f"Captured {len(records)} raw tiles.")


if __name__ == "__main__":
    main()


