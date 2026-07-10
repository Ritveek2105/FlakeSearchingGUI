import subprocess
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent


def run_stage(name: str, script: str):
    print("\n" + "=" * 70)
    print(f"RUNNING: {name}")
    print("=" * 70)

    result = subprocess.run(
        [sys.executable, script],
        cwd=PROJECT_DIR,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Stage failed: {name}")

    print(f"FINISHED: {name}")


def main():
    run_stage("Stage 1 - Correct Tiles", "pipeline_core/stages/stage1_correct_tiles.py")
    run_stage("Stage 2 - Fiji Stitch", "pipeline_core/stages/stage2_fiji_stitch.py")
    run_stage("Stage 3 - Post-Stitch Correction", "pipeline_core/stages/stage3_post_correct.py")
    run_stage("Stage 4 - Roboflow Detection", "pipeline_core/stages/stage4_roboflow_detect.py")
    run_stage("Stage 5 - Merge JSON", "pipeline_core/stages/stage5_merge_json.py")
    run_stage("Stage 6 - Generate DZI", "pipeline_core/stages/stage6_generate_dzi.py")
    run_stage("Stage 7 - Update Website", "pipeline_core/stages/stage7_update_website.py")

    print("\nPipeline complete.")


if __name__ == "__main__":
    main()