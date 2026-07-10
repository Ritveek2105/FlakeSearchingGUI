from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SampleConfig:
    sample_name: str = ""
    material_type: str = "graphene"
    objective: str = "20x"
    camera: str = "AmScope MU1203-BI"
    operator: str = "Jason Zheng"
    notes: str = ""


@dataclass
class InputConfig:
    raw_folder: str = ""
    raw_file_pattern: str = "{p}_graphene.jpg"
    corrected_file_pattern: str = "{p}_graphene_corrected.tif"


@dataclass
class StitchingConfig:
    grid_size_x: int = 6
    grid_size_y: int = 4
    tile_overlap: int = 40
    scan_order: str = "HORIZONTALCONTINUOUS"
    grid_origin: str = "UL"
    first_tile_index: int = 1


@dataclass
class AcquisitionConfig:
    enabled: bool = False
    output_folder: str = ""
    serial_port: str = "COM3"
    baudrate: int = 115200
    step_x: int = 0
    step_y: int = 0
    settle_seconds: float = 0.5
    serpentine: bool = True


@dataclass
class DetectionConfig:
    #
    # Detection mode
    #
    # "manual"
    # "roboflow"
    #
    mode: str = "manual"

    #
    # Roboflow settings
    #
    roboflow_confidence: float = 0.35
    roboflow_model_id: str = "grapheneflakes-72y6l-szuyj/2"
    tile_size: int = 1024
    tile_overlap: int = 200


@dataclass
class PublishConfig:
    mode: str = "new"
    sample_id: str | None = None


@dataclass
class RunConfig:
    sample: SampleConfig = field(default_factory=SampleConfig)
    input: InputConfig = field(default_factory=InputConfig)
    stitching: StitchingConfig = field(default_factory=StitchingConfig)
    acquisition: AcquisitionConfig = field(default_factory=AcquisitionConfig)
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    publish: PublishConfig = field(default_factory=PublishConfig)


def save_run_config(path: Path, config: RunConfig) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(config), f, indent=2)

    return path


def load_run_config(path: Path) -> RunConfig:
    with open(path, "r", encoding="utf-8") as f:
        data: dict[str, Any] = json.load(f)

    return RunConfig(
        sample=SampleConfig(**data.get("sample", {})),
        input=InputConfig(**data.get("input", {})),
        stitching=StitchingConfig(**data.get("stitching", {})),
        acquisition=AcquisitionConfig(**data.get("acquisition", {})),
        detection=DetectionConfig(**data.get("detection", {})),
        publish=PublishConfig(**data.get("publish", {})),
    )
