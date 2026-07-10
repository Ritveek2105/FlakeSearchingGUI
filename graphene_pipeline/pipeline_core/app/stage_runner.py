import subprocess
import sys
from pathlib import Path


class StageRunner:
    def __init__(self, project_root: Path):
        self.project_root = project_root

    def run(self, script_name: str, extra_args: list[str] | None = None) -> None:
        module_name = f"pipeline_core.stages.{Path(script_name).stem}"

        cmd = [sys.executable, "-m", module_name]

        if extra_args:
            cmd.extend(extra_args)

        print("Running:")
        print(" ".join(cmd))

        result = subprocess.run(
            cmd,
            cwd=self.project_root,
            text=True,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"Stage failed: {script_name}, return code {result.returncode}"
            )
