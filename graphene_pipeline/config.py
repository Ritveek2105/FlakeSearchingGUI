import os
from pathlib import Path

# =====================================================
# Project Root
# =====================================================

def _env_path(name: str, default: Path | None = None) -> Path | None:
    value = os.environ.get(name)
    if not value:
        return default
    return Path(value).expanduser()


PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = _env_path("GRAPHENE_PIPELINE_HOME", Path.cwd()).resolve()
DEFAULT_WEBSITE_DIR = PROJECT_DIR.parent / "stitched-ui"


def _website_dir() -> Path:
    return _env_path("GRAPHENE_WEBSITE_DIR", DEFAULT_WEBSITE_DIR)


def _website_public_dir() -> Path:
    return _env_path("GRAPHENE_WEBSITE_PUBLIC_DIR", _website_dir() / "public")

# =====================================================
# Paths
# =====================================================

PATHS = {
    "project": PROJECT_DIR,
    "data": PROJECT_DIR / "data",
    "logs": PROJECT_DIR / "logs",
    "reports": PROJECT_DIR / "reports",

    "raw_tiles": PROJECT_DIR / "data" / "raw_tiles",
    "corrected_tiles": PROJECT_DIR / "data" / "corrected_tiles",
    "flake_masks": PROJECT_DIR / "data" / "flake_masks",
    "bare_chip_points": PROJECT_DIR / "data" / "bare_chip_points",

    "stitched": PROJECT_DIR / "data" / "stitched_images",
    "post_corrected": PROJECT_DIR / "data" / "post_corrected",

    "tile_json": PROJECT_DIR / "data" / "tile_json",
    "tile_previews": PROJECT_DIR / "data" / "tile_previews",

    "dzi": PROJECT_DIR / "data" / "dzi",
    "exports": PROJECT_DIR / "data" / "exports",

    "website": _website_dir(),
    "website_public": _website_public_dir(),
}

# =====================================================
# General Image Settings
# =====================================================

IMAGE = {
    "valid_extensions": [".png", ".jpg", ".jpeg", ".tif", ".tiff"],
    "sample_type": "graphene",
    "objective": "20x",
    "camera": "AmScope MU1203-BI",
}

# =====================================================
# Stage 1: Individual Tile Illumination Correction
# =====================================================

TILE_CORRECTION = {
    # Flake mask tuning
    "color_distance_percentile": 88,
    "morph_gradient_percentile": 88,
    "min_flake_size": 80,
    "hole_size": 150,

    # Morphology kernel sizes
    "gradient_kernel_size": 7,
    "close_kernel_size": 9,
    "open_kernel_size": 3,
    "safety_dilation_kernel_size": 9,

    # Grid-block bare-chip selection
    "block_size": 80,
    "candidates_per_block": 150,
    "patch_radius": 3,
    "max_texture_allowed": 6,
    "max_bare_points": 8000,

    # Illumination smoothing
    "illumination_smoothing_sigma": 45,

    # Surface fitting speed control. The illumination field is very smooth,
    # so fitting on a smaller grid and resizing is much faster than dense
    # full-resolution interpolation.
    "illumination_surface_max_side": 768,
}


# ============================================================
# Stage 1.5 — MIST / Fiji stitching settings
# ============================================================

FIJI_EXE = os.environ.get("FIJI_EXE") or os.environ.get("FIJI_PATH") or "fiji"

FIJI_GRID_SIZE_X = 6
FIJI_GRID_SIZE_Y = 4
FIJI_TILE_OVERLAP = 40
FIJI_FILE_PATTERN = "{p}_graphene_corrected.tif"
FIJI_FIRST_TILE_INDEX = 1
FIJI_SCAN_ORDER = "HORIZONTALCONTINUOUS"
FIJI_OUTPUT_NAME = "Fused_graphene.tif"


# =====================================================
# Stage 2: Stitched Image Analysis
# =====================================================

STITCHED_ANALYSIS = {

    "input_stitched_name": "Fused.tif",

    "output_corrected_name": "Fused_corrected.tif",

    "preview_name": "stitched_preview.png",

    "corrected_preview_name": "stitched_corrected_preview.png",

    "illumination_preview_name": "stitched_estimated_illumination.png",

    "bare_points_preview_name": "stitched_bare_chip_points.png",

    "flake_mask_name": "stitched_flake_mask.png",

    "correction_strength": 1.0,

    # Stage 2 uses the same coarse-surface optimization as Stage 1, but allows
    # a larger grid because stitched mosaics cover a wider field.
    "illumination_surface_max_side": 1024,
}

# =====================================================
# Stage 3: Roboflow Flake Detection
# =====================================================

ROBOFLOW = {
    "model_id": "grapheneflakes-72y6l-szuyj/2",
    "confidence": 0.35,
    "api_url": "https://detect.roboflow.com",

    # Tiling settings
    "tile_size": 1024,
    "tile_overlap": 200,

    # Save individual tile PNGs for debugging
    "save_tile_images": True,

    # API key should NOT be hardcoded here.
    # Set it in PowerShell before running detection:
    # $env:ROBOFLOW_API_KEY="your_key_here"
}

# =====================================================
# Stage 3: Detection Merge / Export
# =====================================================

JSON_MERGE = {
    "final_json_name": "flakes.json",
    "deduplicate": True,
    "duplicate_distance_px": 50,
}

# =====================================================
# Stage 5: Generate DeepZoom / DZI
# =====================================================

GENERATE_DZI = {
    "input_image_name": "Fused_corrected.tif",
    "dzi_basename": "Fused",
    "tile_size": 254,
    "overlap": 1,
    "tile_format": "png",
    "jpeg_quality": 90,
}

# =====================================================
# Stage 6: Publish Sample to Website
# =====================================================

PUBLISH_SAMPLE = {
    "sample_prefix": "graphene",
    "published_dzi_name": "image.dzi",
    "published_dzi_files_name": "image_files",
    "published_preview_name": "preview.png",
    "metadata_name": "metadata.json",
    "samples_catalog_name": "samples.json",
}

# =====================================================
# Stage 7: Website Export
# =====================================================

WEBSITE = {
    "public_dir": PATHS["website_public"],
    "dzi_basename": "Fused",
    "flakes_json_name": "flakes.json",
}

