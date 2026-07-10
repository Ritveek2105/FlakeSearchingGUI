from __future__ import annotations

from pathlib import Path

from pipeline_core.app.services.configuration_service import ConfigurationService
from pipeline_core.app.services.models import LoadProfileInput, SaveProfileInput
from pipeline_core.runtime.run_config import RunConfig


class ProfileManager:
    """GUI compatibility wrapper around ConfigurationService."""

    def __init__(self, project_root: Path):
        self.service = ConfigurationService(project_root)
        self.profile_dir = self.service.profile_dir

    def list_profiles(self) -> list[str]:
        return self.service.list_profiles()

    def profile_path(self, name: str) -> Path:
        return self.service.profile_path(name)

    def exists(self, name: str) -> bool:
        return self.service.exists(name)

    def load_profile(self, name: str) -> RunConfig:
        return self.service.load_profile(
            LoadProfileInput(name=name)
        ).config

    def save_profile(self, name: str, config: RunConfig) -> None:
        self.service.save_profile(
            SaveProfileInput(name=name, config=config)
        )

    def delete_profile(self, name: str) -> None:
        self.service.delete_profile(name)

    def rename_profile(
        self,
        old_name: str,
        new_name: str,
    ) -> None:
        self.service.rename_profile(old_name, new_name)
