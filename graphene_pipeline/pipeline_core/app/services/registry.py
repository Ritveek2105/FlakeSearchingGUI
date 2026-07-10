from __future__ import annotations

from pipeline_core.app.services.models import (
    AgentToolSpec,
    CancelPipelineInput,
    ComputeChipPlaneInput,
    DeleteFilesInput,
    ExportPreviewInput,
    ExportYoloDatasetInput,
    MoveStageInput,
    PublishSampleInput,
    StagePositionInput,
    StartScanInput,
    StartPipelineInput,
    UploadToRoboflowInput,
    ValidationInput,
    dataclass_json_schema,
)


class AgentToolRegistry:
    def __init__(self) -> None:
        self._tools = [
            self._tool(
                name="validate_pipeline_settings",
                description="Validate a RunConfig without starting a pipeline run.",
                input_model=ValidationInput,
                require_confirmation=False,
            ),
            self._tool(
                name="start_pipeline_run",
                description="Start pipeline execution from a RunConfig.",
                input_model=StartPipelineInput,
                require_confirmation=True,
            ),
            self._tool(
                name="cancel_pipeline_run",
                description="Cancel a running pipeline job.",
                input_model=CancelPipelineInput,
                require_confirmation=False,
            ),
            self._tool(
                name="compute_chip_plane",
                description="Compute a chip plane from three stage-coordinate corners.",
                input_model=ComputeChipPlaneInput,
                require_confirmation=False,
            ),
            self._tool(
                name="read_stage_position",
                description="Read the current microscope stage position. Currently returns a safe stub.",
                input_model=StagePositionInput,
                require_confirmation=False,
            ),
            self._tool(
                name="publish_sample",
                description="Publish existing pipeline outputs to the website sample folder.",
                input_model=PublishSampleInput,
                require_confirmation=True,
            ),
            self._tool(
                name="generate_export_preview",
                description="Preview YOLO/Roboflow tile export counts for a published sample.",
                input_model=ExportPreviewInput,
                require_confirmation=False,
            ),
            self._tool(
                name="export_yolo_dataset",
                description="Export a YOLO/Roboflow dataset zip from manual annotation boxes.",
                input_model=ExportYoloDatasetInput,
                require_confirmation=False,
            ),
            self._tool(
                name="move_stage",
                description="Reserved future tool for microscope stage movement.",
                input_model=MoveStageInput,
                require_confirmation=True,
            ),
            self._tool(
                name="start_scan",
                description="Reserved future tool for starting microscope acquisition scans.",
                input_model=StartScanInput,
                require_confirmation=True,
            ),
            self._tool(
                name="delete_files",
                description="Reserved future tool for deleting generated files.",
                input_model=DeleteFilesInput,
                require_confirmation=True,
            ),
            self._tool(
                name="overwrite_sample",
                description="Reserved future tool for overwriting an existing website sample.",
                input_model=PublishSampleInput,
                require_confirmation=True,
            ),
            self._tool(
                name="upload_to_roboflow",
                description="Reserved future tool for uploading exported training data to Roboflow.",
                input_model=UploadToRoboflowInput,
                require_confirmation=True,
            ),
        ]

    def list_tools(self) -> list[AgentToolSpec]:
        return list(self._tools)

    def get_tool(self, name: str) -> AgentToolSpec:
        for tool in self._tools:
            if tool.name == name:
                return tool
        raise KeyError(f"Unknown tool: {name}")

    def _tool(
        self,
        name: str,
        description: str,
        input_model: type,
        require_confirmation: bool,
    ) -> AgentToolSpec:
        return AgentToolSpec(
            name=name,
            description=description,
            input_model=input_model,
            input_schema=dataclass_json_schema(input_model),
            require_confirmation=require_confirmation,
        )
