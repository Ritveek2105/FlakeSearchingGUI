from __future__ import annotations

import shutil
from pathlib import Path

from config import PATHS

from pipeline_core.app.progress import ProgressManager
from pipeline_core.app.stage_runner import StageRunner
from pipeline_core.acquisition.amscope_camera import AmScopeCamera
from pipeline_core.acquisition.chip_scanner import ChipScanner, RasterScanConfig
from pipeline_core.acquisition.serial_stage import ArduinoStageController

from pipeline_core.runtime.context import RunContext
from pipeline_core.runtime.validator import (
    print_validation_result,
    validate_run_config,
)
from pipeline_core.runtime.context import RunContext


STAGES = [
    ("stage1", "Stage 1: Correct Tiles", "stage1_correct_tiles.py"),
    ("stage1_5", "Stage 1.5: Stitch Tiles", "stage1_5_stitch_tiles_mist.py"),
    ("stage2", "Stage 2: Analyze Stitched Image", "stage2_analyze_stitched.py"),
    ("stage3", "Stage 3: Detect Flakes", "stage3_detect_flakes.py"),
    ("stage5", "Stage 5: Generate DZI", "stage5_generate_dzi.py"),
    ("stage6", "Stage 6: Publish Sample", "stage6_publish_sample.py"),
]


def should_run_stage(config, script_name: str) -> bool:
    detection_mode = config.detection.mode.lower().strip()

    if script_name == "stage3_detect_flakes.py" and detection_mode == "manual":
        return False

    return True


class PipelineRunner:
    def __init__(self, context: RunContext):
        self.context = context
        self.stage_runner = StageRunner(context.project_root)
        self.progress = ProgressManager(context.status_path)

    def clear_folder(self, folder: Path) -> None:
        folder.mkdir(parents=True, exist_ok=True)

        for item in folder.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)

    def scan_raw_tiles(self) -> None:
        acquisition = self.context.config.acquisition
        output_dir = Path(acquisition.output_folder or self.context.config.input.raw_folder or PATHS["raw_tiles"])
        destination = PATHS["raw_tiles"]
        self.clear_folder(output_dir)
        if output_dir.resolve() != destination.resolve():
            self.clear_folder(destination)
        scan_config = RasterScanConfig(
            output_dir=output_dir,
            file_pattern=self.context.config.input.raw_file_pattern,
            grid_size_x=self.context.config.stitching.grid_size_x,
            grid_size_y=self.context.config.stitching.grid_size_y,
            step_x=acquisition.step_x,
            step_y=acquisition.step_y,
            overlap_percent=self.context.config.stitching.tile_overlap,
            settle_seconds=acquisition.settle_seconds,
            first_tile_index=self.context.config.stitching.first_tile_index,
            serpentine=acquisition.serpentine,
        )
        with ArduinoStageController(
            port=acquisition.serial_port,
            baudrate=acquisition.baudrate,
        ) as stage:
            with AmScopeCamera() as camera:
                records = ChipScanner(stage, camera).run(scan_config)
        if output_dir.resolve() != destination.resolve():
            valid_exts = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
            for file in output_dir.iterdir():
                if file.is_file() and file.suffix.lower() in valid_exts:
                    shutil.copy2(file, destination / file.name)

        self.progress.add(
            "stage0",
            "complete",
            f"Captured {len(records)} raw tiles to {destination}",
        )

    def copy_raw_tiles(self) -> None:
        raw_folder = Path(self.context.config.input.raw_folder)

        if not raw_folder.exists():
            raise FileNotFoundError(f"Raw folder does not exist: {raw_folder}")

        valid_exts = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}

        files = [
            p for p in raw_folder.iterdir()
            if p.is_file() and p.suffix.lower() in valid_exts
        ]

        if not files:
            raise RuntimeError(f"No image files found in raw folder: {raw_folder}")

        destination = PATHS["raw_tiles"]

# Prevent accidentally deleting the source folder if the user
# passes data/raw_tiles as the input folder.
        if raw_folder.resolve() == destination.resolve():
            self.progress.add(
                "input",
                "skipped",
                "Raw folder is already the pipeline input folder; skipping copy.",
            )
            return

        self.clear_folder(destination)

        for file in files:
            shutil.copy2(file, destination / file.name)

        self.progress.add(
            "input",
            "complete",
            f"Copied {len(files)} raw tiles to {destination}",
        )
                

    def run_all(self, skip_copy: bool = False) -> None:
        self.progress.add("pipeline", "started", "Full pipeline started")

        self.progress.add("validation", "started", "Validating run configuration")

        validation = validate_run_config(self.context.config)
        print_validation_result(validation)

        if not validation.ok:
            self.progress.add("validation", "failed", "Validation failed")
            raise RuntimeError("Pipeline validation failed. See errors above.")

        self.progress.add("validation", "complete", "Validation passed")

        if self.context.config.acquisition.enabled:
            self.progress.add("stage0", "started", "Stage 0: Scan Chip")
            self.scan_raw_tiles()
            self.progress.add("input", "skipped", "Raw tiles acquired from microscope")
        elif not skip_copy:
            self.copy_raw_tiles()
        else:
            self.progress.add("input", "skipped", "Using existing data/raw_tiles folder")


        for stage_key, stage_label, script_name in STAGES:
            if not should_run_stage(self.context.config, script_name):
                self.progress.add(
                    stage_key,
                    "skipped",
                    f"{stage_label} skipped for manual annotation mode",
                )
                continue

            self.progress.add(stage_key, "started", stage_label)

            extra_args = ["--run-config", str(self.context.run_config_path)]

            if script_name == "stage6_publish_sample.py":
                publish = self.context.config.publish

                if publish.mode == "republish" and publish.sample_id:
                    extra_args.extend(["--sample", publish.sample_id])

            try:
                self.stage_runner.run(script_name, extra_args=extra_args)
            except Exception:
                self.progress.add(stage_key, "failed", stage_label)
                raise

            self.progress.add(stage_key, "complete", stage_label)

        self.progress.add("pipeline", "complete", "Full pipeline complete")
