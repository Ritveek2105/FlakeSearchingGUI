from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Tuple

import numpy as np
from PIL import Image


Image.MAX_IMAGE_PIXELS = None


@dataclass
class Tile:
    tile_id: str
    image: np.ndarray
    x0: int
    y0: int
    width: int
    height: int


def load_rgb_image(path: Path) -> np.ndarray:
    """
    Load a stitched TIFF or image file as RGB uint8.
    """
    img = Image.open(path).convert("RGB")
    return np.array(img)


def generate_tiles(
    image: np.ndarray,
    tile_size: int = 1024,
    overlap: int = 200,
) -> Iterator[Tile]:
    """
    Split a large RGB image into overlapping inference tiles.

    Coordinates:
        x0, y0 are the tile's top-left position in the full stitched image.
    """
    if overlap >= tile_size:
        raise ValueError("overlap must be smaller than tile_size")

    h, w = image.shape[:2]
    step = tile_size - overlap

    tile_index = 0

    y_positions = list(range(0, max(h - tile_size, 0) + 1, step))
    x_positions = list(range(0, max(w - tile_size, 0) + 1, step))

    if not y_positions or y_positions[-1] + tile_size < h:
        y_positions.append(max(h - tile_size, 0))

    if not x_positions or x_positions[-1] + tile_size < w:
        x_positions.append(max(w - tile_size, 0))

    for y0 in y_positions:
        for x0 in x_positions:
            tile_img = image[y0:y0 + tile_size, x0:x0 + tile_size]

            th, tw = tile_img.shape[:2]

            yield Tile(
                tile_id=f"tile_{tile_index:05d}",
                image=tile_img,
                x0=x0,
                y0=y0,
                width=tw,
                height=th,
            )

            tile_index += 1


def save_tile_png(tile: Tile, output_dir: Path) -> Path:
    """
    Save a tile image as PNG for Roboflow inference/debugging.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    tile_path = output_dir / f"{tile.tile_id}.png"
    Image.fromarray(tile.image).save(tile_path)

    return tile_path
