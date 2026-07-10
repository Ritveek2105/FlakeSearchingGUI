from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pipeline_core.runtime.run_config import RunConfig


@dataclass
class RunContext:
    project_root: Path
    run_dir: Path
    run_config_path: Path
    config: RunConfig

    @property
    def log_dir(self) -> Path:
        return self.run_dir / "logs"

    @property
    def status_path(self) -> Path:
        return self.run_dir / "status.json"
