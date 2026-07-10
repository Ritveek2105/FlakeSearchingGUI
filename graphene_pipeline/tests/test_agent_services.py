from pathlib import Path

from PIL import Image

from pipeline_core.app.services.acquisition_service import AcquisitionService
from pipeline_core.app.services.export_service import (
    AnnotationBox,
    TileSpec,
    build_tiles,
    intersect_box_with_tile,
    yolo_line,
)
from pipeline_core.app.services.models import (
    ComputeChipPlaneInput,
    Point3DInput,
    StagePositionInput,
    ValidationInput,
)
from pipeline_core.app.services.pipeline_execution_service import PipelineExecutionService
from pipeline_core.app.services.registry import AgentToolRegistry
from pipeline_core.runtime.run_config import RunConfig


def test_registry_marks_risky_tools():
    registry = AgentToolRegistry()
    risky = {
        tool.name
        for tool in registry.list_tools()
        if tool.require_confirmation
    }

    assert "start_pipeline_run" in risky
    assert "move_stage" in risky
    assert "start_scan" in risky
    assert "delete_files" in risky
    assert "overwrite_sample" in risky
    assert "upload_to_roboflow" in risky
    assert registry.get_tool("validate_pipeline_settings").require_confirmation is False


def test_acquisition_service_computes_plane():
    service = AcquisitionService()
    result = service.compute_chip_plane(
        ComputeChipPlaneInput(
            corners=[
                Point3DInput(0, 0, 0),
                Point3DInput(1, 0, 0),
                Point3DInput(0, 1, 1),
            ]
        )
    )

    assert result.equation
    assert result.c != 0


def test_acquisition_service_computes_best_fit_plane_from_extra_corners():
    service = AcquisitionService()
    result = service.compute_chip_plane(
        ComputeChipPlaneInput(
            corners=[
                Point3DInput(0, 0, 0),
                Point3DInput(1, 0, 0),
                Point3DInput(0, 1, 1),
                Point3DInput(1, 1, 1),
            ]
        )
    )

    assert result.equation
    assert result.c != 0


def test_stage_position_is_safe_stub():
    result = AcquisitionService().read_stage_position(request=StagePositionInput())

    assert result.is_stub is True
    assert result.x is None


def test_pipeline_validation_service_returns_typed_output(tmp_path: Path):
    service = PipelineExecutionService(tmp_path)
    result = service.validate_pipeline_settings(ValidationInput(config=RunConfig()))

    assert isinstance(result.ok, bool)
    assert isinstance(result.errors, list)
    assert isinstance(result.warnings, list)


def test_export_pure_functions():
    tiles = build_tiles(image_width=1000, image_height=800, tile_size=640, overlap=64)
    assert tiles[0] == TileSpec(x=0, y=0, width=640, height=640)

    clipped = intersect_box_with_tile(
        AnnotationBox(x=600, y=20, width=100, height=50, label="graphene"),
        tiles[0],
    )

    assert clipped is not None
    assert clipped.width == 40
    assert yolo_line(clipped, 0, tiles[0]).startswith("0 ")


def test_export_service_writes_png_yolo_zip(tmp_path: Path):
    from pipeline_core.app.services.export_service import ExportService
    from pipeline_core.app.services.models import ExportYoloDatasetInput
    import json
    import zipfile

    sample_dir = tmp_path / "samples" / "graphene_000001"
    sample_dir.mkdir(parents=True)
    Image.new("RGB", (800, 600), "white").save(sample_dir / "source.tif")
    (sample_dir / "metadata.json").write_text(
        json.dumps({"image": {"width": 800, "height": 600, "source_image": "source.tif"}}),
        encoding="utf-8",
    )
    (sample_dir / "annotations.json").write_text(
        json.dumps({"version": 1, "boxes": [{"x": 100, "y": 100, "width": 80, "height": 60, "label": "graphene"}]}),
        encoding="utf-8",
    )

    output = ExportService().export_yolo_dataset(
        ExportYoloDatasetInput(sample_dir=sample_dir, valid_percent=0)
    )

    with zipfile.ZipFile(output.output_zip) as archive:
        names = archive.namelist()

    assert any(name.endswith(".png") for name in names)
    assert not any(name.endswith(".jpg") for name in names)
    assert "data.yaml" in names
