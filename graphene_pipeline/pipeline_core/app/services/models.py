from __future__ import annotations

from dataclasses import MISSING, asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any, get_args, get_origin, get_type_hints

from pipeline_core.runtime.run_config import RunConfig


@dataclass(frozen=True)
class ValidationInput:
    config: RunConfig


@dataclass(frozen=True)
class ValidationOutput:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class StartPipelineInput:
    config: RunConfig
    skip_copy: bool = False
    background: bool = True


@dataclass(frozen=True)
class PipelineJobOutput:
    job_id: str
    run_dir: Path
    run_config_path: Path
    status_path: Path


@dataclass(frozen=True)
class CancelPipelineInput:
    job_id: str


@dataclass(frozen=True)
class CancelPipelineOutput:
    job_id: str
    cancelled: bool
    message: str = ""


@dataclass(frozen=True)
class Point3DInput:
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class ComputeChipPlaneInput:
    corners: list[Point3DInput]


@dataclass(frozen=True)
class ComputeChipPlaneOutput:
    a: float
    b: float
    c: float
    d: float
    equation: str


@dataclass(frozen=True)
class StagePositionInput:
    controller_id: str | None = None


@dataclass(frozen=True)
class StagePositionOutput:
    x: float | None
    y: float | None
    z: float | None
    is_stub: bool
    message: str


@dataclass(frozen=True)
class PublishSampleInput:
    config: RunConfig
    sample_id: str | None = None


@dataclass(frozen=True)
class PublishSampleOutput:
    sample_id: str | None
    return_code: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class ExportPreviewInput:
    sample_dir: Path
    tile_size: int = 640
    overlap: int = 64
    min_box_size: int = 5
    skip_empty_tiles: bool = True


@dataclass(frozen=True)
class ExportPreviewOutput:
    sample_id: str
    image_width: int
    image_height: int
    tile_size: int
    overlap: int
    stride: int
    total_tiles: int
    exported_tiles: int
    empty_tiles: int
    annotated_tiles: int
    total_boxes: int
    exported_box_instances: int
    class_counts: dict[str, int]


@dataclass(frozen=True)
class ExportYoloDatasetInput:
    sample_dir: Path
    output_zip: Path | None = None
    tile_size: int = 640
    overlap: int = 64
    min_box_size: int = 5
    skip_empty_tiles: bool = True
    valid_percent: int = 20


@dataclass(frozen=True)
class ExportYoloDatasetOutput:
    output_zip: Path
    exported_tiles: int
    train_tiles: int
    valid_tiles: int
    classes: list[str]


@dataclass(frozen=True)
class AgentToolSpec:
    name: str
    description: str
    input_model: type
    input_schema: dict[str, Any]
    require_confirmation: bool = False


@dataclass(frozen=True)
class MoveStageInput:
    x: float | None = None
    y: float | None = None
    z: float | None = None
    relative: bool = False


@dataclass(frozen=True)
class StartScanInput:
    config: RunConfig


@dataclass(frozen=True)
class DeleteFilesInput:
    target_path: Path
    recursive: bool = False


@dataclass(frozen=True)
class UploadToRoboflowInput:
    dataset_zip: Path
    project_id: str
    batch_name: str | None = None


@dataclass(frozen=True)
class SaveProfileInput:
    name: str
    config: RunConfig


@dataclass(frozen=True)
class SaveProfileOutput:
    name: str
    path: Path


@dataclass(frozen=True)
class LoadProfileInput:
    name: str


@dataclass(frozen=True)
class LoadProfileOutput:
    name: str
    config: RunConfig
    path: Path


def dataclass_to_dict(value: Any) -> dict[str, Any]:
    if not is_dataclass(value):
        raise TypeError("Expected a dataclass instance.")
    return asdict(value)


def dataclass_json_schema(model: type) -> dict[str, Any]:
    if not is_dataclass(model):
        raise TypeError(f"{model!r} is not a dataclass type.")

    properties: dict[str, Any] = {}
    required: list[str] = []

    type_hints = get_type_hints(model)

    for name, field_info in model.__dataclass_fields__.items():
        properties[name] = _type_to_schema(type_hints.get(name, field_info.type))
        if field_info.default is MISSING and field_info.default_factory is MISSING:
            required.append(name)

    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
    }

    if required:
        schema["required"] = required

    return schema


def _type_to_schema(annotation: Any) -> dict[str, Any]:
    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin in (list, list):
        item_type = args[0] if args else Any
        return {"type": "array", "items": _type_to_schema(item_type)}

    if origin in (dict, dict):
        return {"type": "object"}

    if origin is tuple:
        return {"type": "array"}

    if origin is not None and type(None) in args:
        non_none = [arg for arg in args if arg is not type(None)]
        schema = _type_to_schema(non_none[0]) if non_none else {}
        schema["nullable"] = True
        return schema

    if annotation in (str, Path):
        return {"type": "string"}
    if annotation is int:
        return {"type": "integer"}
    if annotation is float:
        return {"type": "number"}
    if annotation is bool:
        return {"type": "boolean"}
    if is_dataclass(annotation):
        return dataclass_json_schema(annotation)

    return {"type": "object"}
