from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pipeline_core.app.pipeline_runner import PipelineRunner
from pipeline_core.app.services.models import (
    CancelPipelineInput,
    CancelPipelineOutput,
    PipelineJobOutput,
    StartPipelineInput,
    ValidationInput,
    ValidationOutput,
)
from pipeline_core.runtime.context import RunContext
from pipeline_core.runtime.run_config import RunConfig, save_run_config
from pipeline_core.runtime.validator import validate_run_config


@dataclass
class ManagedPipelineJob:
    job_id: str
    run_dir: Path
    run_config_path: Path
    status_path: Path
    process: subprocess.Popen | None = None

    def to_output(self) -> PipelineJobOutput:
        return PipelineJobOutput(
            job_id=self.job_id,
            run_dir=self.run_dir,
            run_config_path=self.run_config_path,
            status_path=self.status_path,
        )


class PipelineExecutionService:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.jobs: dict[str, ManagedPipelineJob] = {}

    def create_context(self, config: RunConfig) -> RunContext:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = self.project_root / "runs" / f"run_{timestamp}"
        run_config_path = run_dir / "run_config.json"

        save_run_config(run_config_path, config)

        return RunContext(
            project_root=self.project_root,
            run_dir=run_dir,
            run_config_path=run_config_path,
            config=config,
        )

    def validate_pipeline_settings(self, request: ValidationInput) -> ValidationOutput:
        result = validate_run_config(request.config)
        return ValidationOutput(
            ok=result.ok,
            errors=list(result.errors),
            warnings=list(result.warnings),
        )

    def start_pipeline_run(self, request: StartPipelineInput) -> PipelineJobOutput:
        context = self.create_context(request.config)
        job_id = context.run_dir.name

        if request.background:
            process = self._start_background_process(
                config=request.config,
                run_config_path=context.run_config_path,
                skip_copy=request.skip_copy,
            )

            job = ManagedPipelineJob(
                job_id=job_id,
                run_dir=context.run_dir,
                run_config_path=context.run_config_path,
                status_path=context.status_path,
                process=process,
            )
            self.jobs[job_id] = job
            return job.to_output()

        runner = PipelineRunner(context)
        runner.run_all(skip_copy=request.skip_copy)
        job = ManagedPipelineJob(
            job_id=job_id,
            run_dir=context.run_dir,
            run_config_path=context.run_config_path,
            status_path=context.status_path,
            process=None,
        )
        self.jobs[job_id] = job
        return job.to_output()

    def cancel_pipeline_run(self, request: CancelPipelineInput) -> CancelPipelineOutput:
        job = self.jobs.get(request.job_id)

        if not job:
            return CancelPipelineOutput(
                job_id=request.job_id,
                cancelled=False,
                message="Pipeline job was not found.",
            )

        if job.process and job.process.poll() is None:
            job.process.terminate()
            return CancelPipelineOutput(
                job_id=request.job_id,
                cancelled=True,
                message="Cancel requested.",
            )

        return CancelPipelineOutput(
            job_id=request.job_id,
            cancelled=False,
            message="Pipeline job is not running.",
        )

    def get_job(self, job_id: str) -> ManagedPipelineJob:
        return self.jobs[job_id]

    def _start_background_process(
        self,
        config: RunConfig,
        run_config_path: Path,
        skip_copy: bool,
    ) -> subprocess.Popen:
        cmd = [
            sys.executable,
            "-u",
            "-m",
            "pipeline_core.stages.run_full_pipeline",
            "--run-config",
            str(run_config_path),
            "--raw-folder",
            config.input.raw_folder,
        ]

        if skip_copy:
            cmd.append("--skip-copy")

        cmd.extend(
            [
                "--sample-name",
                config.sample.sample_name,
                "--material-type",
                config.sample.material_type,
                "--objective",
                config.sample.objective,
                "--camera",
                config.sample.camera,
                "--operator",
                config.sample.operator,
                "--notes",
                config.sample.notes,
                "--grid-size-x",
                str(config.stitching.grid_size_x),
                "--grid-size-y",
                str(config.stitching.grid_size_y),
                "--tile-overlap",
                str(config.stitching.tile_overlap),
                "--scan-order",
                config.stitching.scan_order,
                "--grid-origin",
                config.stitching.grid_origin,
                "--first-tile-index",
                str(config.stitching.first_tile_index),
                "--raw-file-pattern",
                config.input.raw_file_pattern,
                "--corrected-file-pattern",
                config.input.corrected_file_pattern,
                "--detection-mode",
                config.detection.mode,
                "--roboflow-confidence",
                str(config.detection.roboflow_confidence),
                "--roboflow-model-id",
                config.detection.roboflow_model_id,
                "--inference-tile-size",
                str(config.detection.tile_size),
                "--inference-tile-overlap",
                str(config.detection.tile_overlap),
            ]
        )

        if config.publish.mode == "republish" and config.publish.sample_id:
            cmd.extend(["--publish-sample", config.publish.sample_id])

        return subprocess.Popen(
            cmd,
            cwd=self.project_root,
            text=True,
        )
