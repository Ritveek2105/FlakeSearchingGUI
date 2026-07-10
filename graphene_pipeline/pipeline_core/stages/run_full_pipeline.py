import argparse
import sys
from datetime import datetime
from pathlib import Path


from config import PROJECT_DIR

PROJECT_ROOT = PROJECT_DIR


from pipeline_core.app.pipeline_runner import PipelineRunner
from pipeline_core.runtime.context import RunContext
from pipeline_core.runtime.run_config import (
    DetectionConfig,
    InputConfig,
    PublishConfig,
    RunConfig,
    SampleConfig,
    StitchingConfig,
    load_run_config,
    save_run_config,
)


def build_run_config(args: argparse.Namespace) -> RunConfig:
    publish_mode = "republish" if args.publish_sample else "new"

    return RunConfig(
        sample=SampleConfig(
            sample_name=args.sample_name,
            material_type=args.material_type,
            objective=args.objective,
            camera=args.camera,
            operator=args.operator,
            notes=args.notes,
        ),
        input=InputConfig(
            raw_folder=str(args.raw_folder),
            raw_file_pattern=args.raw_file_pattern,
            corrected_file_pattern=args.corrected_file_pattern,
        ),
        stitching=StitchingConfig(
            grid_size_x=args.grid_size_x,
            grid_size_y=args.grid_size_y,
            tile_overlap=args.tile_overlap,
            scan_order=args.scan_order,
            grid_origin=args.grid_origin,
            first_tile_index=args.first_tile_index,
        ),
        detection=DetectionConfig(
            mode=args.detection_mode,
            roboflow_confidence=args.roboflow_confidence,
            roboflow_model_id=args.roboflow_model_id,
            tile_size=args.inference_tile_size,
            tile_overlap=args.inference_tile_overlap,
        ),
        publish=PublishConfig(
            mode=publish_mode,
            sample_id=args.publish_sample,
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the full graphene image-processing pipeline."
    )

    parser.add_argument("--raw-folder", required=True, type=Path)
    parser.add_argument("--skip-copy", action="store_true")
    parser.add_argument(
        "--run-config",
        type=Path,
        default=None,
        help="Use an existing run_config.json and write status.json beside it.",
    )

    parser.add_argument("--sample-name", default="")
    parser.add_argument("--material-type", default="graphene")
    parser.add_argument("--objective", default="20x")
    parser.add_argument("--camera", default="AmScope MU1203-BI")
    parser.add_argument("--operator", default="Jason Zheng")
    parser.add_argument("--notes", default="")

    parser.add_argument("--grid-size-x", default=6, type=int)
    parser.add_argument("--grid-size-y", default=4, type=int)
    parser.add_argument("--tile-overlap", default=40, type=int)
    parser.add_argument("--scan-order", default="HORIZONTALCONTINUOUS")
    parser.add_argument("--grid-origin", default="UL", choices=["UL", "UR", "LL", "LR"])
    parser.add_argument("--first-tile-index", default=1, type=int)

    parser.add_argument("--raw-file-pattern", default="{p}_graphene.jpg")
    parser.add_argument("--corrected-file-pattern", default="{p}_graphene_corrected.tif")

    parser.add_argument(
        "--detection-mode",
        default="manual",
        choices=["manual", "roboflow"],
    )

    parser.add_argument("--roboflow-confidence", default=0.35, type=float)
    parser.add_argument(
        "--roboflow-model-id",
        default="grapheneflakes-72y6l-szuyj/2",
    )
    parser.add_argument("--inference-tile-size", default=1024, type=int)
    parser.add_argument("--inference-tile-overlap", default=200, type=int)

    parser.add_argument(
        "--publish-sample",
        default=None,
        help="Existing sample ID to republish. Leave blank to publish new sample.",
    )

    args = parser.parse_args()

    if args.run_config:
        run_config_path = args.run_config.resolve()
        run_dir = run_config_path.parent
        run_config = load_run_config(run_config_path)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = PROJECT_ROOT / "runs" / f"run_{timestamp}"

        run_config = build_run_config(args)
        run_config_path = save_run_config(run_dir / "run_config.json", run_config)

    context = RunContext(
        project_root=PROJECT_ROOT,
        run_dir=run_dir,
        run_config_path=run_config_path,
        config=run_config,
    )

    print("=" * 80)
    print("Stage 7A: Full Graphene Pipeline Runner")
    print("=" * 80)
    print(f"Run folder: {run_dir}")
    print(f"Run config: {run_config_path}")

    runner = PipelineRunner(context)
    runner.run_all(skip_copy=args.skip_copy)

    print("=" * 80)
    print("Pipeline complete")
    print("=" * 80)
    print(f"Run folder: {run_dir}")
    print("Refresh the website to view the published sample.")


if __name__ == "__main__":
    main()
