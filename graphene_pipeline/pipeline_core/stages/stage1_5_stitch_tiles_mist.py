from pathlib import Path
import argparse
import shutil
import subprocess
import sys

import numpy as np
import tifffile


from config import PROJECT_DIR

PROJECT_ROOT = PROJECT_DIR


from config import FIJI_EXE
from pipeline_core.runtime.run_config import RunConfig, load_run_config


CORRECTED_TILES_DIR = PROJECT_ROOT / "data" / "corrected_tiles"
STITCHED_OUTPUT_DIR = PROJECT_ROOT / "data" / "stitched_images"
MACRO_PATH = PROJECT_ROOT / "pipeline_core" / "fiji_macros" / "mist_stitch_tiles.ijm"


def ensure_folders() -> None:
    STITCHED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MACRO_PATH.parent.mkdir(parents=True, exist_ok=True)


def clear_stitched_outputs() -> None:
    STITCHED_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for item in STITCHED_OUTPUT_DIR.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)


def expected_corrected_tile_paths(run_config: RunConfig) -> list[Path]:
    pattern = run_config.input.corrected_file_pattern
    first = run_config.stitching.first_tile_index
    total = run_config.stitching.grid_size_x * run_config.stitching.grid_size_y

    return [
        CORRECTED_TILES_DIR / pattern.replace("{p}", str(p))
        for p in range(first, first + total)
    ]


def validate_corrected_tiles(run_config: RunConfig) -> None:
    expected_paths = expected_corrected_tile_paths(run_config)
    missing = [p.name for p in expected_paths if not p.exists()]
    actual_tiles = sorted(CORRECTED_TILES_DIR.glob("*.tif"))

    if missing:
        actual_examples = "\n".join(p.name for p in actual_tiles[:10])

        raise FileNotFoundError(
            "MIST expected corrected tiles that do not exist.\n\n"
            f"Grid size: {run_config.stitching.grid_size_x} x {run_config.stitching.grid_size_y}\n"
            f"Expected tile count: {len(expected_paths)}\n"
            f"Corrected tile pattern: {run_config.input.corrected_file_pattern}\n\n"
            "Missing examples:\n"
            + "\n".join(missing[:10])
            + "\n\nActual corrected tile examples:\n"
            + (actual_examples if actual_examples else "No corrected TIFF files found.")
        )

    print(f"Validated {len(expected_paths)} corrected tiles.")


def validate_grid_origin(grid_origin: str) -> str:
    grid_origin = grid_origin.upper().strip()

    if grid_origin not in {"UL", "UR", "LL", "LR"}:
        raise ValueError(
            f"Invalid grid origin: {grid_origin}. Use one of: UL, UR, LL, LR."
        )

    return grid_origin


def mist_path(path: Path) -> str:
    return f"[{path.resolve().as_posix()}]"


def mist_value(value: str) -> str:
    return f"[{value}]"


def write_mist_macro(run_config: RunConfig) -> None:
    input_dir = mist_path(CORRECTED_TILES_DIR)
    output_dir = mist_path(STITCHED_OUTPUT_DIR)

    grid_x = run_config.stitching.grid_size_x
    grid_y = run_config.stitching.grid_size_y
    overlap = run_config.stitching.tile_overlap
    scan_order = run_config.stitching.scan_order
    grid_origin = validate_grid_origin(run_config.stitching.grid_origin)
    first_tile = run_config.stitching.first_tile_index
    file_pattern = mist_value(run_config.input.corrected_file_pattern)

    macro_text = f"""
run("MIST", "gridwidth={grid_x} "
+ "gridheight={grid_y} "
+ "starttile={first_tile} "
+ "imagedir={input_dir} "
+ "filenamepattern={file_pattern} "
+ "filenamepatterntype=SEQUENTIAL "
+ "gridorigin={grid_origin} "
+ "assemblefrommetadata=false "
+ "assemblenooverlap=false "
+ "globalpositionsfile=[] "
+ "numberingpattern={scan_order} "
+ "startrow=0 "
+ "startcol=0 "
+ "extentwidth={grid_x} "
+ "extentheight={grid_y} "
+ "timeslices=0 "
+ "istimeslicesenabled=false "
+ "outputpath={output_dir} "
+ "displaystitching=false "
+ "outputfullimage=true "
+ "outputmeta=true "
+ "outputimgpyramid=true "
+ "blendingmode=LINEAR "
+ "blendingalpha=NaN "
+ "compressionmode=UNCOMPRESSED "
+ "outfileprefix=img- "
+ "unit=MICROMETER "
+ "unitx=1.0 "
+ "unity=1.0 "
+ "programtype=AUTO "
+ "numcputhreads=12 "
+ "loadfftwplan=false "
+ "savefftwplan=false "
+ "stagerepeatability=0 "
+ "horizontaloverlap={overlap} "
+ "verticaloverlap={overlap} "
+ "numfftpeaks=0 "
+ "overlapuncertainty=NaN "
+ "isusedoubleprecision=false "
+ "isusebioformats=false "
+ "issuppressmodelwarningdialog=false "
+ "isenablecudaexceptions=false "
+ "translationrefinementmethod=SINGLE_HILL_CLIMB "
+ "numtranslationrefinementstartpoints=16 "
+ "headless=false "
+ "loglevel=MANDATORY "
+ "debuglevel=NONE");
"""

    MACRO_PATH.write_text(macro_text, encoding="utf-8")
    print(f"MIST macro written to: {MACRO_PATH}")


def export_rgb_tiff() -> None:
    candidates = sorted(STITCHED_OUTPUT_DIR.glob("*stitched*.ome.tif"))

    if not candidates:
        raise FileNotFoundError(
            "MIST finished without creating a stitched OME-TIFF.\n\n"
            f"Expected output folder:\n{STITCHED_OUTPUT_DIR}\n\n"
            "The most likely cause is that MIST could not match the corrected "
            "tile filenames to the grid. Check the Grid Size X/Y, First Tile "
            "Index, and Corrected File Pattern values."
        )

    ome_path = candidates[-1]
    rgb_tiff_path = STITCHED_OUTPUT_DIR / "Fused.tif"

    print(f"Converting {ome_path.name} to normal RGB TIFF...")

    image = tifffile.imread(ome_path)

    if image.ndim == 3 and image.shape[0] in (3, 4):
        image = np.moveaxis(image, 0, -1)

    if image.ndim == 3 and image.shape[-1] == 4:
        image = image[:, :, :3]

    if image.ndim == 2:
        image = np.stack([image, image, image], axis=-1)

    if image.ndim != 3 or image.shape[-1] != 3:
        raise RuntimeError(f"Could not convert image to RGB. Shape was: {image.shape}")

    tifffile.imwrite(
        rgb_tiff_path,
        image,
        photometric="rgb",
        metadata=None,
    )

    print(f"RGB TIFF saved to: {rgb_tiff_path}")


def run_mist() -> None:
    fiji_command = shutil.which(FIJI_EXE)
    fiji_path = Path(FIJI_EXE).expanduser()

    if fiji_command is None:
        if not fiji_path.exists():
            raise FileNotFoundError(
                "Fiji executable not found. Set FIJI_EXE or FIJI_PATH to the "
                "Fiji executable, or add Fiji to PATH."
            )
        fiji_command = str(fiji_path)

    command = [
        fiji_command,
        "--headless",
        "-macro",
        str(MACRO_PATH),
    ]

    print("Running MIST stitching...")
    print(" ".join(command))

    subprocess.run(command, check=True, cwd=PROJECT_ROOT)
    export_rgb_tiff()

    print("MIST finished.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-config", type=Path, default=None)
    args = parser.parse_args()

    run_config = load_run_config(args.run_config) if args.run_config else RunConfig()

    print("=" * 70)
    print("Stage 1.5: MIST Stitching")
    print("=" * 70)
    print(f"Grid: {run_config.stitching.grid_size_x} x {run_config.stitching.grid_size_y}")
    print(f"Overlap: {run_config.stitching.tile_overlap}")
    print(f"Scan order: {run_config.stitching.scan_order}")
    print(f"Grid origin: {run_config.stitching.grid_origin}")
    print(f"First tile index: {run_config.stitching.first_tile_index}")
    print(f"Corrected tile pattern: {run_config.input.corrected_file_pattern}")

    ensure_folders()
    clear_stitched_outputs()
    validate_corrected_tiles(run_config)
    write_mist_macro(run_config)
    run_mist()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Stage 1.5 MIST failed: {e}")
        sys.exit(1)
