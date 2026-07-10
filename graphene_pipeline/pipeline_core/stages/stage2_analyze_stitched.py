from pathlib import Path
import sys
import json
from datetime import datetime

import numpy as np


# =====================================================
# Project bootstrap
# =====================================================

from config import PROJECT_DIR

PROJECT_ROOT = PROJECT_DIR


# =====================================================
# Project imports
# =====================================================

from config import STITCHED_ANALYSIS

from pipeline_core.stitched_analysis.io import (
    load_rgb_tiff,
    save_preview,
)

from pipeline_core.stitched_analysis.inspect import (
    inspect_image,
)

from pipeline_core.stitched_analysis.illumination import (
    estimate_stitched_illumination,
    normalize_to_uint8,
    mask_to_uint8,
)

from pipeline_core.stitched_analysis.correction import (
    correct_l_channel_lab,
    save_corrected_tiff,
)


# =====================================================
# Paths
# =====================================================

STITCHED_IMAGE_PATH = (
    PROJECT_ROOT
    / "data"
    / "stitched_images"
    / STITCHED_ANALYSIS["input_stitched_name"]
)

CORRECTED_IMAGE_PATH = (
    PROJECT_ROOT
    / "data"
    / "stitched_images"
    / STITCHED_ANALYSIS["output_corrected_name"]
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "stage2_outputs"
)

REPORTS_DIR = (
    PROJECT_ROOT
    / "reports"
)


# =====================================================
# Helpers
# =====================================================

def ensure_folders() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    CORRECTED_IMAGE_PATH.parent.mkdir(parents=True, exist_ok=True)


def write_report(report: dict) -> Path:
    report_path = (
        REPORTS_DIR
        / f"stage2_analyze_stitched_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)

    return report_path


# =====================================================
# Main
# =====================================================

def main() -> None:
    ensure_folders()

    print("=" * 60)
    print("Stage 2 - Analyze Stitched Image")
    print("=" * 60)

    print("\nLoading stitched RGB image...")
    print(f"Input path:")
    print(f"    {STITCHED_IMAGE_PATH}")

    if not STITCHED_IMAGE_PATH.exists():
        raise FileNotFoundError(
            f"Stage 2 input image was not found:\n{STITCHED_IMAGE_PATH}"
        )

    image_rgb = load_rgb_tiff(STITCHED_IMAGE_PATH)

    image_info = inspect_image(image_rgb)

    print(f"Image size : {image_info['width']} x {image_info['height']}")
    print(f"Channels   : {image_info['channels']}")
    print(f"Dtype      : {image_info['dtype']}")

    print("\nSaving RGB preview...")

    preview_path = save_preview(
        image_rgb,
        OUTPUT_DIR / STITCHED_ANALYSIS["preview_name"],
    )

    print("\nEstimating stitched-image illumination...")

    results = estimate_stitched_illumination(image_rgb)

    illumination = results["illumination_L"]
    flake_mask = results["flake_mask"]
    bare_points = results["bare_points"]
    bare_overlay = results["bare_points_overlay"]

    print("\nApplying L-channel illumination correction...")

    corrected_rgb, corrected_lab = correct_l_channel_lab(
        results["lab"],
        illumination,
        correction_strength=STITCHED_ANALYSIS["correction_strength"],
    )

    save_corrected_tiff(
        corrected_rgb,
        CORRECTED_IMAGE_PATH,
    )

    print("Corrected TIFF saved.")

    print("\nSaving diagnostic outputs...")

    illumination_path = save_preview(
        normalize_to_uint8(illumination),
        OUTPUT_DIR / STITCHED_ANALYSIS["illumination_preview_name"],
    )

    flake_mask_path = save_preview(
        mask_to_uint8(flake_mask),
        OUTPUT_DIR / STITCHED_ANALYSIS["flake_mask_name"],
    )

    bare_overlay_path = save_preview(
        bare_overlay,
        OUTPUT_DIR / STITCHED_ANALYSIS["bare_points_preview_name"],
    )

    corrected_preview_path = save_preview(
        corrected_rgb,
        OUTPUT_DIR / STITCHED_ANALYSIS["corrected_preview_name"],
    )

    report = {
        "stage": "stage2_analyze_stitched",
        "status": "success",
        "timestamp": datetime.now().isoformat(),

        "input_path": str(STITCHED_IMAGE_PATH),
        "corrected_image_path": str(CORRECTED_IMAGE_PATH),

        "preview_path": str(preview_path),
        "corrected_preview_path": str(corrected_preview_path),
        "illumination_preview_path": str(illumination_path),
        "flake_mask_path": str(flake_mask_path),
        "bare_points_overlay_path": str(bare_overlay_path),

        "correction_strength": float(STITCHED_ANALYSIS["correction_strength"]),
        "num_bare_points": int(len(bare_points)),

        "image_info": image_info,

        "illumination_L_min": float(np.min(illumination)),
        "illumination_L_max": float(np.max(illumination)),
        "illumination_L_range": float(
            np.max(illumination) - np.min(illumination)
        ),
        "illumination_L_std": float(
            np.std(illumination)
        ),
    }

    report_path = write_report(report)

    print("\nFinished successfully.")

    print("\nOriginal preview:")
    print(f"    {preview_path}")

    print("\nCorrected TIFF:")
    print(f"    {CORRECTED_IMAGE_PATH}")

    print("\nCorrected preview:")
    print(f"    {corrected_preview_path}")

    print("\nFlake mask:")
    print(f"    {flake_mask_path}")

    print("\nBare chip points:")
    print(f"    {bare_overlay_path}")

    print("\nIllumination estimate:")
    print(f"    {illumination_path}")

    print("\nReport:")
    print(f"    {report_path}")


if __name__ == "__main__":
    try:
        main()

    except Exception as e:
        print(f"\nStage 2 failed:\n{e}")
        sys.exit(1)
