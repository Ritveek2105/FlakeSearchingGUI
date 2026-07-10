from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from pipeline_core.app.services.models import PublishSampleInput, PublishSampleOutput
from pipeline_core.runtime.run_config import save_run_config


class PublishService:
    def __init__(self, project_root: Path):
        self.project_root = project_root

    def publish_sample(self, request: PublishSampleInput) -> PublishSampleOutput:
        run_dir = self.project_root / "runs" / "agent_publish"
        run_config_path = save_run_config(run_dir / "run_config.json", request.config)

        cmd = [
            sys.executable,
            "-m",
            "pipeline_core.stages.stage6_publish_sample",
            "--run-config",
            str(run_config_path),
        ]

        if request.sample_id:
            cmd.extend(["--sample", request.sample_id])

        result = subprocess.run(
            cmd,
            cwd=self.project_root,
            text=True,
            capture_output=True,
        )

        if result.returncode != 0:
            raise RuntimeError(
                "Publish sample failed.\n"
                f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
            )

        return PublishSampleOutput(
            sample_id=request.sample_id or request.config.publish.sample_id,
            return_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        )
