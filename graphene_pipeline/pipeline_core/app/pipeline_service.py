from __future__ import annotations

import os
import subprocess
import webbrowser
from pathlib import Path

from config import WEBSITE
from pipeline_core.app.services.models import (
    CancelPipelineInput,
    StartPipelineInput,
    ValidationInput,
)
from pipeline_core.app.services.pipeline_execution_service import (
    ManagedPipelineJob,
    PipelineExecutionService,
)
from pipeline_core.runtime.context import RunContext
from pipeline_core.runtime.run_config import RunConfig


PipelineJob = ManagedPipelineJob


class PipelineService:
    """Compatibility facade used by the Tkinter GUI.

    Reusable backend execution methods live in
    pipeline_core.app.services.pipeline_execution_service. This facade keeps the
    existing GUI call sites and return shapes stable.
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.execution = PipelineExecutionService(project_root)
        self.jobs = self.execution.jobs

    def create_context(self, config: RunConfig) -> RunContext:
        return self.execution.create_context(config)

    def validate(self, config: RunConfig):
        return self.execution.validate_pipeline_settings(
            ValidationInput(config=config)
        )

    def run_blocking(self, config: RunConfig, skip_copy: bool = False) -> RunContext:
        output = self.execution.start_pipeline_run(
            StartPipelineInput(
                config=config,
                skip_copy=skip_copy,
                background=False,
            )
        )
        return RunContext(
            project_root=self.project_root,
            run_dir=output.run_dir,
            run_config_path=output.run_config_path,
            config=config,
        )

    def start_background(
        self,
        config: RunConfig,
        skip_copy: bool = False,
    ) -> PipelineJob:
        output = self.execution.start_pipeline_run(
            StartPipelineInput(
                config=config,
                skip_copy=skip_copy,
                background=True,
            )
        )
        return self.execution.get_job(output.job_id)

    def get_status_path(self, job_id: str) -> Path:
        return self.execution.get_job(job_id).status_path

    def cancel(self, job_id: str) -> None:
        self.execution.cancel_pipeline_run(CancelPipelineInput(job_id=job_id))

    def open_website(self) -> None:
        website_root = Path(WEBSITE["public_dir"]).parent
        website_url = "http://localhost:3000"

        if not hasattr(self, "website_process"):
            self.website_process = None

        website_running = False

        try:
            import urllib.request

            with urllib.request.urlopen(website_url, timeout=2):
                website_running = True
        except Exception:
            website_running = False

        if not website_running:
            self.website_process = subprocess.Popen(
                ["npm", "run", "dev"],
                cwd=website_root,
                shell=True,
            )

            import time
            time.sleep(5)

        webbrowser.open(website_url)

    def open_samples_folder(self) -> None:
        samples_dir = Path(WEBSITE["public_dir"]) / "samples"
        samples_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(samples_dir)

    def open_run_folder(self, job: PipelineJob) -> None:
        if job.run_dir.exists():
            os.startfile(job.run_dir)
