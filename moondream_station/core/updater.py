from pydantic import BaseModel
from packaging.version import Version

from .. import __version__


class UpdateInfo(BaseModel):
    current_version: str
    latest_version: str
    has_update: bool
    update_url: str = ""
    changelog: str = ""
    message: str = ""


class UpdateChecker:
    def __init__(self, config, manifest_manager=None):
        self.config = config
        self.manifest_manager = manifest_manager
        self.current_version = __version__

    def check_for_updates(self) -> UpdateInfo:
        """Check for available updates from manifest"""
        if not self.manifest_manager:
            return UpdateInfo(
                current_version=self.current_version,
                latest_version=self.current_version,
                has_update=False,
                message="No manifest available",
            )

        manifest = self.manifest_manager.get_manifest()
        if not manifest or not manifest.moondream_station_info:
            return UpdateInfo(
                current_version=self.current_version,
                latest_version=self.current_version,
                has_update=False,
                message="Version info not available in manifest",
            )

        try:
            latest_version = manifest.moondream_station_info.get("latest_version", self.current_version)
            has_update = self._compare_versions(self.current_version, latest_version)

            return UpdateInfo(
                current_version=self.current_version,
                latest_version=latest_version,
                has_update=has_update,
                update_url="https://pypi.org/project/moondream-station/",
                changelog="",
            )

        except Exception:
            return UpdateInfo(
                current_version=self.current_version,
                latest_version=self.current_version,
                has_update=False,
                message="Error checking for updates",
            )

    def _compare_versions(self, current: str, latest: str) -> bool:
        """Compare version strings to determine if update is available"""
        try:
            return Version(latest) > Version(current)
        except Exception:
            return False
