from __future__ import annotations

import json
import io
import zipfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from pipeline_core.app.services.models import (
    ExportPreviewInput,
    ExportPreviewOutput,
    ExportYoloDatasetInput,
    ExportYoloDatasetOutput,
)


Image.MAX_IMAGE_PIXELS = None


@dataclass(frozen=True)
class AnnotationBox:
    x: float
    y: float
    width: float
    height: float
    label: str = "graphene"


@dataclass(frozen=True)
class TileBox:
    x: float
    y: float
    width: float
    height: float
    label: str


@dataclass(frozen=True)
class TileSpec:
    x: int
    y: int
    width: int
    height: int


def build_tiles(image_width: int, image_height: int, tile_size: int, overlap: int) -> list[TileSpec]:
    if tile_size <= 0:
        raise ValueError("tile_size must be positive.")
    if overlap < 0 or overlap >= tile_size:
        raise ValueError("overlap must be non-negative and smaller than tile_size.")

    stride = tile_size - overlap
    tiles: list[TileSpec] = []

    y = 0
    while y < image_height:
        x = 0
        while x < image_width:
            tiles.append(
                TileSpec(
                    x=x,
                    y=y,
                    width=min(tile_size, image_width - x),
                    height=min(tile_size, image_height - y),
                )
            )

            if x + tile_size >= image_width:
                break
            x += stride

        if y + tile_size >= image_height:
            break
        y += stride

    return tiles


def intersect_box_with_tile(box: AnnotationBox, tile: TileSpec) -> TileBox | None:
    x1 = max(box.x, tile.x)
    y1 = max(box.y, tile.y)
    x2 = min(box.x + box.width, tile.x + tile.width)
    y2 = min(box.y + box.height, tile.y + tile.height)

    width = x2 - x1
    height = y2 - y1

    if width <= 0 or height <= 0:
        return None

    return TileBox(
        x=x1 - tile.x,
        y=y1 - tile.y,
        width=width,
        height=height,
        label=box.label,
    )


def yolo_line(box: TileBox, class_index: int, tile: TileSpec) -> str:
    x_center = (box.x + box.width / 2) / tile.width
    y_center = (box.y + box.height / 2) / tile.height
    width = box.width / tile.width
    height = box.height / tile.height

    return (
        f"{class_index} "
        f"{x_center:.6f} "
        f"{y_center:.6f} "
        f"{width:.6f} "
        f"{height:.6f}"
    )


def clean_name(value: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in "-_" else "_" for char in value)
    return cleaned.strip("_") or "dataset"


class ExportService:
    def generate_export_preview(self, request: ExportPreviewInput) -> ExportPreviewOutput:
        context = self._load_context(request.sample_dir)
        export_items = self._build_export_items(
            boxes=context["boxes"],
            image_width=context["image_width"],
            image_height=context["image_height"],
            tile_size=request.tile_size,
            overlap=request.overlap,
            min_box_size=request.min_box_size,
            skip_empty_tiles=request.skip_empty_tiles,
        )

        class_counts: dict[str, int] = {}
        annotated_tiles = 0
        exported_box_instances = 0

        for _, boxes in export_items:
            if boxes:
                annotated_tiles += 1
            exported_box_instances += len(boxes)
            for box in boxes:
                class_counts[box.label] = class_counts.get(box.label, 0) + 1

        total_tiles = len(build_tiles(
            context["image_width"],
            context["image_height"],
            request.tile_size,
            request.overlap,
        ))

        return ExportPreviewOutput(
            sample_id=context["sample_id"],
            image_width=context["image_width"],
            image_height=context["image_height"],
            tile_size=request.tile_size,
            overlap=request.overlap,
            stride=request.tile_size - request.overlap,
            total_tiles=total_tiles,
            exported_tiles=len(export_items),
            empty_tiles=total_tiles - len(export_items) if request.skip_empty_tiles else 0,
            annotated_tiles=annotated_tiles,
            total_boxes=len(context["boxes"]),
            exported_box_instances=exported_box_instances,
            class_counts=class_counts,
        )

    def export_yolo_dataset(self, request: ExportYoloDatasetInput) -> ExportYoloDatasetOutput:
        context = self._load_context(request.sample_dir)
        export_items = self._build_export_items(
            boxes=context["boxes"],
            image_width=context["image_width"],
            image_height=context["image_height"],
            tile_size=request.tile_size,
            overlap=request.overlap,
            min_box_size=request.min_box_size,
            skip_empty_tiles=request.skip_empty_tiles,
        )

        if not export_items:
            raise ValueError("No tiles passed the export filters.")

        classes = sorted({box.label for box in context["boxes"]})
        class_index = {label: index for index, label in enumerate(classes)}
        output_zip = request.output_zip or (
            request.sample_dir / f"{clean_name(context['sample_id'])}-yolo-export.zip"
        )
        output_zip.parent.mkdir(parents=True, exist_ok=True)

        valid_every = max(1, round(100 / request.valid_percent)) if request.valid_percent > 0 else 0
        train_tiles = 0
        valid_tiles = 0

        source = Image.open(context["source_image_path"])
        image = source.convert("RGB")
        source.close()

        try:
            with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for index, (tile, boxes) in enumerate(export_items):
                    split = "valid" if valid_every and index % valid_every == 0 else "train"
                    if split == "valid":
                        valid_tiles += 1
                    else:
                        train_tiles += 1

                    base_name = (
                        f"{clean_name(context['sample_id'])}_"
                        f"{index + 1:05d}_x{tile.x}_y{tile.y}"
                    )
                    crop = image.crop((tile.x, tile.y, tile.x + tile.width, tile.y + tile.height))

                    buffer = io.BytesIO()
                    crop.save(buffer, format="PNG")
                    zf.writestr(f"images/{split}/{base_name}.png", buffer.getvalue())

                    labels = [
                        yolo_line(box, class_index[box.label], tile)
                        for box in boxes
                    ]
                    zf.writestr(f"labels/{split}/{base_name}.txt", "\n".join(labels) + "\n")

                zf.writestr(
                    "data.yaml",
                    "\n".join([
                        "path: .",
                        "train: images/train",
                        "val: images/valid",
                        f"nc: {len(classes)}",
                        f"names: {json.dumps(classes)}",
                        "",
                    ]),
                )
        finally:
            image.close()

        return ExportYoloDatasetOutput(
            output_zip=output_zip,
            exported_tiles=len(export_items),
            train_tiles=train_tiles,
            valid_tiles=valid_tiles,
            classes=classes,
        )

    def _load_context(self, sample_dir: Path) -> dict:
        sample_dir = sample_dir.resolve()
        annotations_path = sample_dir / "annotations.json"
        metadata_path = sample_dir / "metadata.json"

        annotations = _load_json(annotations_path)
        metadata = _load_json(metadata_path)

        image_info = metadata.get("image", {})
        image_width = int(image_info["width"])
        image_height = int(image_info["height"])
        source_image = image_info.get("source_image", "source.tif")
        source_image_path = (sample_dir / source_image).resolve()

        if not source_image_path.exists():
            raise FileNotFoundError(f"Missing source image: {source_image_path}")

        boxes = [
            AnnotationBox(
                x=float(box["x"]),
                y=float(box["y"]),
                width=float(box["width"]),
                height=float(box["height"]),
                label=str(box.get("label") or "graphene"),
            )
            for box in annotations.get("boxes", [])
            if float(box.get("width", 0)) > 0 and float(box.get("height", 0)) > 0
        ]

        return {
            "sample_id": sample_dir.name,
            "image_width": image_width,
            "image_height": image_height,
            "source_image_path": source_image_path,
            "boxes": boxes,
        }

    def _build_export_items(
        self,
        boxes: list[AnnotationBox],
        image_width: int,
        image_height: int,
        tile_size: int,
        overlap: int,
        min_box_size: int,
        skip_empty_tiles: bool,
    ) -> list[tuple[TileSpec, list[TileBox]]]:
        export_items: list[tuple[TileSpec, list[TileBox]]] = []

        for tile in build_tiles(image_width, image_height, tile_size, overlap):
            tile_boxes = [
                clipped
                for box in boxes
                if (clipped := intersect_box_with_tile(box, tile)) is not None
                and clipped.width >= min_box_size
                and clipped.height >= min_box_size
            ]

            if tile_boxes or not skip_empty_tiles:
                export_items.append((tile, tile_boxes))

        return export_items


def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)
