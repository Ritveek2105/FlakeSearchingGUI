import argparse
import math
import sys
import shutil
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image


from config import PROJECT_DIR

PROJECT_ROOT = PROJECT_DIR


from config import PATHS, GENERATE_DZI


Image.MAX_IMAGE_PIXELS = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage 5: generate DeepZoom / DZI assets.")
    parser.add_argument(
        "--run-config",
        default=None,
        help="Optional runtime config path. Accepted for Stage 7 app compatibility.",
    )
    return parser.parse_args()


def save_tile(tile, path: Path, tile_format: str, jpeg_quality: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if tile_format.lower() in ["jpg", "jpeg"]:
        tile = tile.convert("RGB")
        tile.save(path, "JPEG", quality=jpeg_quality)
    elif tile_format.lower() == "png":
        tile.save(path, "PNG")
    else:
        raise ValueError(f"Unsupported tile format: {tile_format}")


def write_dzi_file(
    dzi_path: Path,
    width: int,
    height: int,
    tile_size: int,
    overlap: int,
    tile_format: str,
) -> None:
    dzi_path.parent.mkdir(parents=True, exist_ok=True)

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Image TileSize="{tile_size}" Overlap="{overlap}" Format="{escape(tile_format)}" xmlns="http://schemas.microsoft.com/deepzoom/2008">
  <Size Width="{width}" Height="{height}"/>
</Image>
"""

    dzi_path.write_text(xml, encoding="utf-8")


def generate_dzi(
    image_path: Path,
    output_dir: Path,
    basename: str,
    tile_size: int,
    overlap: int,
    tile_format: str,
    jpeg_quality: int,
) -> None:
    if not image_path.exists():
        raise FileNotFoundError(f"Missing input image:\n{image_path}")

    output_dir.mkdir(parents=True, exist_ok=True)

    dzi_path = output_dir / f"{basename}.dzi"
    tiles_root = output_dir / f"{basename}_files"

    if dzi_path.exists():
        dzi_path.unlink()

    if tiles_root.exists():
        shutil.rmtree(tiles_root)

    print(f"Loading image:")
    print(f"  {image_path}")

    img = Image.open(image_path).convert("RGB")
    width, height = img.size

    print(f"Image size: {width} x {height}")

    max_dim = max(width, height)
    max_level = math.ceil(math.log2(max_dim))

    print(f"Generating DeepZoom pyramid:")
    print(f"  levels: {max_level + 1}")
    print(f"  tile size: {tile_size}")
    print(f"  overlap: {overlap}")
    print(f"  format: {tile_format}")

    extension = "jpeg" if tile_format.lower() == "jpeg" else tile_format.lower()

    for level in range(max_level + 1):
        scale = 2 ** (max_level - level)

        level_width = max(1, math.ceil(width / scale))
        level_height = max(1, math.ceil(height / scale))

        print(f"Level {level}: {level_width} x {level_height}")

        if level == max_level:
            level_img = img
        else:
            level_img = img.resize(
                (level_width, level_height),
                Image.Resampling.LANCZOS,
            )

        cols = math.ceil(level_width / tile_size)
        rows = math.ceil(level_height / tile_size)

        level_dir = tiles_root / str(level)

        for col in range(cols):
            for row in range(rows):
                x0 = max(0, col * tile_size - overlap)
                y0 = max(0, row * tile_size - overlap)
                x1 = min(level_width, (col + 1) * tile_size + overlap)
                y1 = min(level_height, (row + 1) * tile_size + overlap)

                tile = level_img.crop((x0, y0, x1, y1))

                tile_path = level_dir / f"{col}_{row}.{extension}"

                save_tile(
                    tile=tile,
                    path=tile_path,
                    tile_format=tile_format,
                    jpeg_quality=jpeg_quality,
                )

    write_dzi_file(
        dzi_path=dzi_path,
        width=width,
        height=height,
        tile_size=tile_size,
        overlap=overlap,
        tile_format=tile_format,
    )

    print(f"DZI saved:")
    print(f"  {dzi_path}")
    print(f"Tiles saved:")
    print(f"  {tiles_root}")


def main() -> None:
    parse_args()
    print("=" * 70)
    print("Stage 5: Generate DeepZoom / DZI")
    print("=" * 70)

    image_path = PATHS["stitched"] / GENERATE_DZI["input_image_name"]

    output_dir = PATHS["dzi"]

    generate_dzi(
        image_path=image_path,
        output_dir=output_dir,
        basename=GENERATE_DZI["dzi_basename"],
        tile_size=int(GENERATE_DZI["tile_size"]),
        overlap=int(GENERATE_DZI["overlap"]),
        tile_format=str(GENERATE_DZI["tile_format"]),
        jpeg_quality=int(GENERATE_DZI["jpeg_quality"]),
    )

    print("=" * 70)
    print("Stage 5 complete")
    print("=" * 70)


if __name__ == "__main__":
    main()
