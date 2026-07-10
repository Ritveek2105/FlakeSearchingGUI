import sys
from pathlib import Path


from config import PROJECT_DIR

PROJECT_ROOT = PROJECT_DIR


from pipeline_core.app.pipeline_service import PipelineService
from pipeline_core.runtime.run_config import (
    RunConfig,
    InputConfig,
    StitchingConfig,
)


def main() -> None:
    service = PipelineService(PROJECT_ROOT)

    config = RunConfig(
        input=InputConfig(
            raw_folder=str(PROJECT_ROOT / "data" / "raw_tiles"),
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

    result = service.validate(config)

    print("Validation OK:", result.ok)

    if result.errors:
        print("Errors:")
        for error in result.errors:
            print(error)

    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(warning)


if __name__ == "__main__":
    main()
