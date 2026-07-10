from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass
class SampleSection:
    name: str
    material_type: str
    objective: str
    camera: str
    operator: str
    notes: str


@dataclass
class ScanSection:
    grid_size_x: int
    grid_size_y: int
    tile_overlap: int
    scan_order: str
    first_tile_index: int


@dataclass
class DetectionSection:
    model_id: str
    confidence: float
    flake_count: int | None


@dataclass
class ImageSection:
    width: int | None
    height: int | None
    source_image: str


@dataclass
class PublishedSampleMetadata:
    id: str
    published_at: str
    sample: SampleSection
    scan: ScanSection
    detection: DetectionSection
    image: ImageSection

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_sample_metadata(
    sample_id: str,
    run_config,
    source_image: str,
    image_width: int | None,
    image_height: int | None,
    flake_count: int | None,
) -> PublishedSampleMetadata:
    sample_name = run_config.sample.sample_name.strip()

    if not sample_name:
        sample_name = sample_id.replace("_", " ").title()

    return PublishedSampleMetadata(
        id=sample_id,
        published_at=datetime.now().isoformat(timespec="seconds"),
        sample=SampleSection(
            name=sample_name,
            material_type=run_config.sample.material_type,
            objective=run_config.sample.objective,
            camera=run_config.sample.camera,
            operator=run_config.sample.operator,
            notes=run_config.sample.notes,
        ),
        scan=ScanSection(
            grid_size_x=run_config.stitching.grid_size_x,
            grid_size_y=run_config.stitching.grid_size_y,
            tile_overlap=run_config.stitching.tile_overlap,
            scan_order=run_config.stitching.scan_order,
            first_tile_index=run_config.stitching.first_tile_index,
        ),
        detection=DetectionSection(
            model_id=run_config.detection.roboflow_model_id,
            confidence=run_config.detection.roboflow_confidence,
            flake_count=flake_count,
        ),
        image=ImageSection(
            width=image_width,
            height=image_height,
            source_image=source_image,
        ),
    )