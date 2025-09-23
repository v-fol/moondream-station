#!/usr/bin/env python3
import sys
import subprocess
import venv
import json
import uuid
import platform
import contextlib
import requests
from pathlib import Path

import posthog

posthog.disabled = True  # Disable immediately to prevent any auto-uploads

from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.console import Console
from rich import print as rprint

from moondream_station.cli import DEFAULT_MANIFEST_URL


class MoondreamStationLauncher:
    def __init__(self):
        self.app_dir = Path.home() / ".moondream-station"
        self.venv_dir = self.app_dir / "venv"
        self.python_exe = self._get_venv_python()
        self.analytics_client = None
        self.console = Console()
        self._setup_analytics()

    @contextlib.contextmanager
    def spinner(self, message: str):
        """Context manager for spinner display"""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True,
        ) as progress:
            progress.add_task(description=message, total=None)
            yield

    def _setup_analytics(self):
        """Setup analytics from manifest if available"""
        # Check connectivity before setting up PostHog
        try:
            response = requests.get(
                "https://huggingface.co/vikhyatk/moondream2/resolve/main/config.json",
                timeout=2,
            )
            if response.status_code != 200:
                return
        except:
            return

        # Try to load analytics config from manifest
        try:
            manifest_data = None

            # First try to fetch from URL
            try:
                response = requests.get(DEFAULT_MANIFEST_URL, timeout=5)
                response.raise_for_status()
                manifest_data = response.json()
            except:
                # Try cache if URL fails
                cache_file = self.app_dir / "models" / "cache" / "manifests" / "manifest_cache.json"
                if cache_file.exists():
                    with open(cache_file) as f:
                        manifest_data = json.load(f)

            if not manifest_data:
                return

            analytics_config = manifest_data.get("analytics")
            if analytics_config:
                posthog.disabled = False  # Re-enable now that we have connectivity
                posthog.api_key = analytics_config.get("posthog_project_key")
                posthog.host = analytics_config.get(
                    "posthog_host", "https://app.posthog.com"
                )
                posthog.enable_exception_autocapture = True
                self.analytics_client = posthog

                # Get or create user ID
                config_file = self.app_dir / "config.json"
                user_id = None
                if config_file.exists():
                    try:
                        with open(config_file) as f:
                            config = json.load(f)
                        user_id = config.get("user_id")
                    except:
                        pass

                if not user_id:
                    user_id = str(uuid.uuid4())

                self.user_id = user_id
        except Exception:
            pass

    def _track(self, event: str, properties: dict = None):
        """Track analytics event"""
        if not self.analytics_client:
            return

        if properties is None:
            properties = {}

        properties.update(
            {
                "platform": platform.system(),
                "python_version": platform.python_version(),
            }
        )

        try:
            self.analytics_client.capture(
                distinct_id=self.user_id, event=event, properties=properties
            )
        except Exception:
            pass

    def _get_venv_python(self) -> Path:
        """Get path to venv Python executable"""
        if sys.platform == "win32":
            return self.venv_dir / "Scripts" / "python.exe"
        return self.venv_dir / "bin" / "python"

    def _venv_exists(self) -> bool:
        """Check if venv exists and is valid"""
        return self.python_exe.exists() and self.python_exe.is_file()

    def _create_venv(self):
        """Create virtual environment"""
        self._track("env_setup_start")

        self.app_dir.mkdir(exist_ok=True)

        if self.venv_dir.exists():
            import shutil

            shutil.rmtree(self.venv_dir)

        try:
            with self.spinner("Setting up Moondream Station environment"):
                venv.create(self.venv_dir, with_pip=True)
            self._track("env_setup_success")
        except Exception as e:
            self._track("env_setup_failed", {"error": str(e)})
            raise

    def _install_requirements(self):
        """Install required packages from requirements.txt"""
        self._track("requirements_install_start")

        moondream_station_root = Path(__file__).parent.parent
        requirements_file = moondream_station_root / "requirements.txt"

        cmd = [
            str(self.python_exe),
            "-m",
            "pip",
            "install",
            "-r",
            str(requirements_file),
        ]

        with self.spinner("Installing moondream-station requirements"):
            result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            self._track(
                "requirements_install_failed",
                {"error": result.stderr, "returncode": result.returncode},
            )
            rprint(f"[red]❌ Failed to install packages: {result.stderr}[/red]")
            sys.exit(1)
        else:
            self._track("requirements_install_success")

    def _install_moondream_station(self):
        """Install moondream-station package in development mode"""
        moondream_station_root = Path(__file__).parent.parent
        cmd = [
            str(self.python_exe),
            "-m",
            "pip",
            "install",
            "-e",
            str(moondream_station_root),
        ]

        with self.spinner("Installing moondream-station package"):
            result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            rprint(
                f"[red]❌ Failed to install moondream-station: {result.stderr}[/red]"
            )
            sys.exit(1)

    def _install_backend_requirements(self, args: list[str]):
        """Install backend requirements if manifest is specified"""
        manifest_path = None
        for i, arg in enumerate(args):
            if arg in ["--manifest", "-m"] and i + 1 < len(args):
                manifest_path = args[i + 1]
                break

        # Use default manifest URL if none specified
        if not manifest_path:
            manifest_path = DEFAULT_MANIFEST_URL

        try:
            import json
            import requests

            self._track("backend_requirements_start", {"manifest_path": manifest_path})

            with self.spinner("Installing backend requirements"):
                if manifest_path.startswith(("http://", "https://")):
                    response = requests.get(manifest_path, timeout=30)
                    manifest_data = response.json()
                else:
                    with open(manifest_path) as f:
                        manifest_data = json.load(f)

                for backend_id, backend_info in manifest_data.get(
                    "backends", {}
                ).items():
                    requirements_url = backend_info.get("requirements_url")
                    if requirements_url:
                        self._install_requirements_from_url(requirements_url)

            self._track("backend_requirements_success")

        except Exception as e:
            self._track(
                "backend_requirements_failed",
                {"error": str(e), "manifest_path": manifest_path},
            )
            rprint(f"[yellow]⚠️  Could not install backend requirements: {e}[/yellow]")

    def _install_requirements_from_url(self, requirements_url: str):
        """Install requirements from URL or local path"""
        try:
            import requests

            if requirements_url.startswith(("http://", "https://")):
                response = requests.get(requirements_url, timeout=30)
                requirements_content = response.text
            else:
                moondream_station_root = Path(__file__).parent.parent
                requirements_path = moondream_station_root / requirements_url
                with open(requirements_path) as f:
                    requirements_content = f.read()

            import tempfile

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False
            ) as f:
                f.write(requirements_content)
                temp_path = f.name

            cmd = [str(self.python_exe), "-m", "pip", "install", "-r", temp_path]
            result = subprocess.run(cmd, capture_output=True, text=True)

            Path(temp_path).unlink()

            if result.returncode != 0:
                rprint(
                    f"[yellow]⚠️  Some backend requirements failed to install: {result.stderr}[/yellow]"
                )

        except Exception as e:
            rprint(
                f"[yellow]⚠️  Could not install requirements from {requirements_url}: {e}[/yellow]"
            )

    def _setup_environment(self, args: list[str]):
        """Set up the complete environment"""
        if not self._venv_exists():
            self._create_venv()
            self._install_requirements()
            self._install_moondream_station()

        self._install_backend_requirements(args)

    def launch(self, args: list[str]):
        """Launch moondream-station with given arguments"""
        self._track("launcher_start", {"args": len(args)})

        try:
            self._setup_environment(args)

            cmd = [
                str(self.python_exe),
                "-m",
                "moondream_station.cli",
            ] + args

            result = subprocess.run(cmd)
            self._track("launcher_success", {"exit_code": result.returncode})
            sys.exit(result.returncode)
        except KeyboardInterrupt:
            self._track("launcher_interrupted")
            sys.exit(0)
        except Exception as e:
            self._track("launcher_failed", {"error": str(e)})
            raise


def main():
    launcher = MoondreamStationLauncher()
    launcher.launch(sys.argv[1:])


if __name__ == "__main__":
    main()
