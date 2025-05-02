import logging
import time
import os
import tarfile
import sys
import subprocess

from datetime import datetime, timezone
from posthog import Posthog
from typing import Any, Optional

from inferencevisor import InferenceVisor
from clivisor import CLIVisor
from manifest import Manifest
from config import Config
from misc import download_file

logger = logging.getLogger("hypervisor")
HYPERVISOR_VERSION = "v0.0.1"


class Hypervisor:
    """
    Main logical hub for the MD-S.

    Responsible for coordinating all components of the Moondream Station,
    including the inference server, CLI, and handling updates and metrics.
    """

    def __init__(
        self,
    ):
        self.config = Config()
        self.manifest = Manifest()
        self.inferencevisor = InferenceVisor(self.config, self.manifest)
        self.clivisor = CLIVisor(self.config, self.manifest)

        self.posthog = None
        if md_ph_k := os.environ.get("md_ph_k"):
            self.posthog = Posthog(
                md_ph_k,
                host=self.config.posthog_host,
            )

        self.config.active_hypervisor = HYPERVISOR_VERSION
        self.status = "initialized"
        logger.debug("Hypervisor initialized")
        self.posthog_capture("boot")

    def check_health(self) -> dict[str, Any]:
        """
        Check the health of all components.

        Returns:
            dict: Health status of all components including timestamp and overall status
        """
        health = {"hypervisor": "healthy", "timestamp": time.time()}

        try:
            inference_health = self.inferencevisor.check_health()
            health["inference_server"] = inference_health.get(
                "inference_server", "unknown"
            )
        except Exception as e:
            logger.error(f"Error checking inference visor health: {e}")
            health["inference_server"] = "error"

        if any(
            status != "healthy"
            for key, status in health.items()
            if key not in ["timestamp", "status"]
        ):
            health["status"] = "degraded"
        else:
            health["status"] = "healthy"

        return health

    # -------------------- Updates --------------------
    def check_all_for_updates(self):
        """
        Check for updates for all components.

        Returns:
            dict: Update status for bootstrap, hypervisor, model, and CLI
        """
        self.manifest.update()
        ret_value = {}
        ret_value["bootstrap"] = self.check_for_bootstrap_update(False)
        ret_value["hypervisor"] = self.check_for_updates(False)
        ret_value["model"] = self.inferencevisor.check_for_model_updates(False)
        ret_value["cli"] = self.clivisor.check_for_update(False)
        return ret_value

    def check_for_updates(self, update_manifest: bool = True):
        """
        Check for hypervisor updates.

        Args:
            update_manifest: If True, refresh manifest data before checking

        Returns:
            dict: Status containing "ood" (out of date) flag and current version
        """
        if update_manifest:
            self.manifest.update()

        ret_value = {
            "ood": False,
            "version": self.manifest.current_hypervisor["version"],
        }
        if self.config.active_hypervisor != self.manifest.current_hypervisor["version"]:
            ret_value["ood"] = True
        return ret_value

    def check_for_bootstrap_update(self, update_manifest: bool = True):
        """
        Check for bootstrap updates.

        Args:
            update_manifest: If True, refresh manifest data before checking

        Returns:
            dict: Status containing "ood" (out of date) flag and current version
        """
        if update_manifest:
            self.manifest.update()

        ret_value = {
            "ood": False,
            "version": self.manifest.current_bootstrap["version"],
        }
        if self.config.active_bootstrap != self.manifest.current_bootstrap["version"]:
            ret_value["ood"] = True
        return ret_value

    def update_hypervisor(self):
        """
        Update hypervisor to the latest version if needed.

        Downloads and extracts the new hypervisor package, then shuts down
        to allow bootstrap to restart with the new version.
        """
        self.status = "updating hypervisor"
        update_status = self.check_for_updates()
        if not update_status["ood"]:
            print("Hypervisor is already up to date.")
            return
        self._download_and_extract_hypervisor(self.manifest.current_hypervisor["url"])
        self.shutdown()  # Bootstrap should restart hypervisor

    def _download_and_extract_hypervisor(self, url: str) -> bool:
        """
        Download and extract the hypervisor package.

        Args:
            url: URL to download the hypervisor package from

        Returns:
            bool: True if download and extraction succeeded

        Raises:
            Exception: If download or extraction fails
        """
        main_py = "hypervisor_server.py"
        if os.path.isfile(main_py):
            logger.debug(f"'{main_py}' already exists, It will be overwritten.")

        tar_path = os.path.join(self.app_dir, "hypervisor.tar.gz")

        try:
            download_file(url, tar_path, logger)

            logger.debug(f"Extracting hypervisor package to {self.app_dir}")
            with tarfile.open(tar_path, "r:gz") as tar:
                tar.extractall(path=self.app_dir)

            logger.debug("Extraction complete")
            os.remove(tar_path)
            logger.debug(f"Removed {tar_path}")

            return os.path.isfile(main_py)
        except Exception as e:
            logger.error(f"Error downloading/extracting hypervisor package: {e}")
            if os.path.exists(tar_path):
                os.remove(tar_path)
            return False

    def update_bootstrap(self):
        """
        Trigger bootstrap update by exiting with special code.

        Exits with code 99, which signals the bootstrap to check for updates.
        """
        self.status = "updating bootstrap"
        update_status = self.check_for_bootstrap_update()
        if not update_status["ood"]:
            print("Bootstrap is already up to date.")
            self.status = "ok"
            return

        shutdown_result = self.inferencevisor.shutdown()
        logger.info(f"Inference server shutdown result: {shutdown_result}")
        print("Hypervisor exiting 99")
        sys.exit(99)

    # -------------------- Admin --------------------
    @property
    def app_dir(self):
        """
        Get the application directory path.

        Returns:
            str: Path to the Moondream Station application directory
        """
        return os.path.join(os.path.expanduser("~"), "Library", "MoondreamStation")

    def posthog_capture(
        self, event: str, properties: Optional[dict[str, Any]] = None
    ) -> None:
        """
        Send telemetry event to Posthog if metrics reporting is enabled.

        Args:
            event: Event name to record
            properties: Additional properties to include with the event
        """
        if not self.config.metrics_reporting:
            return

        if properties is not None:
            properties = self.config.core_config | properties
        else:
            properties = self.config.core_config

        self.posthog.capture(
            distinct_id=self.config.posthog_did,
            event=event,
            properties=properties,
            timestamp=datetime.now(timezone.utc),
        )

    def reset(self):
        """
        Reset the application by removing the application directory.

        Attempts to delete the app directory and then shuts down the hypervisor.
        """
        try:
            subprocess.run(f"rm -rf {self.app_dir}", shell=True, check=True)
            logger.info(f"Reset app_dir: {self.app_dir}")
            self.shutdown()
        except subprocess.CalledProcessError as e:
            err_msg = (e.stderr or e.stdout or "").strip()
            logger.error("Reset failed (exit %s): %s", e.returncode, err_msg)

    def toggle_posthog_capture(self) -> bool:
        """
        Toggle metrics reporting on/off.

        Returns:
            bool: New state of metrics reporting
        """
        self.config.metrics_reporting = not self.config.metrics_reporting
        return self.config.metrics_reporting

    def boot(self):
        """
        Boot all components of the system.

        Initializes the CLI, inference server, and loads configuration.
        """
        self.clivisor.boot()
        self.inferencevisor.boot()
        self.config.load()

    def shutdown(self):
        """
        Shutdown the hypervisor and all components.

        Shuts down the inference server and exits the process.
        """
        logger.info("Shutting down hypervisor and all components")

        shutdown_result = self.inferencevisor.shutdown()
        logger.info(f"Inference server shutdown result: {shutdown_result}")

        self.status = "off"
        sys.exit(0)
