from __future__ import annotations

from pathlib import Path

from pipeline_core.app.services.models import (
    LoadProfileInput,
    LoadProfileOutput,
    SaveProfileInput,
    SaveProfileOutput,
)
from pipeline_core.runtime.run_config import load_run_config, save_run_config


class ConfigurationService:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.profile_dir = project_root / "profiles"
        self.profile_dir.mkdir(parents=True, exist_ok=True)

    def list_profiles(self) -> list[str]:
        return sorted(profile.stem for profile in self.profile_dir.glob("*.json"))

    def profile_path(self, name: str) -> Path:
        if not name or any(char in name for char in "\\/:*?\"<>|"):
            raise ValueError("Profile name contains invalid characters.")
        return self.profile_dir / f"{name}.json"

    def exists(self, name: str) -> bool:
        return self.profile_path(name).exists()

    def save_profile(self, request: SaveProfileInput) -> SaveProfileOutput:
        path = save_run_config(self.profile_path(request.name), request.config)
        return SaveProfileOutput(name=request.name, path=path)

    def load_profile(self, request: LoadProfileInput) -> LoadProfileOutput:
        path = self.profile_path(request.name)
        return LoadProfileOutput(
            name=request.name,
            config=load_run_config(path),
            path=path,
        )

    def delete_profile(self, name: str) -> None:
        path = self.profile_path(name)
        if path.exists():
            path.unlink()

    def rename_profile(self, old_name: str, new_name: str) -> None:
        self.profile_path(old_name).rename(self.profile_path(new_name))
