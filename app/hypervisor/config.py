import os
import json
import logging
from typing import Dict, Any, Optional
import uuid

DEFAULT_CONFIG = {
    "active_bootstrap": "",
    "active_hypervisor": "",
    "active_inference_client": "",
    "active_model": "",
    "active_cli": "",
    "inference_url": "http://localhost:20200/v1",
    "ph_h": "https://us.i.posthog.com",
    "ph_did": str(uuid.uuid4()),
    "metrics_reporting": True,
}


class Config:
    def __init__(self, path: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        self.data = {}

        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.path = path or os.path.join(base_dir, "data", "config.json")
        _ = self.load()

    def load(self) -> Dict[str, Any]:
        try:
            if os.path.isfile(self.path):
                with open(self.path, "r") as f:
                    self.data = json.load(f)
            else:
                self.logger.debug(f"Config not found at {self.path}, creating default")
                self.data = DEFAULT_CONFIG
                self.save()
            return self.data
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            self.data = DEFAULT_CONFIG
            return self.data

    def save(self) -> bool:
        try:
            with open(self.path, "w") as f:
                json.dump(self.data, f, indent=4)
            return True
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")
            return False

    @property
    def active_model(self) -> str:
        return self.data.get("active_model", "")

    @active_model.setter
    def active_model(self, value: str) -> None:
        self.data["active_model"] = value
        self.save()
        self.logger.debug(f"Set active model to {value}")

    @property
    def active_cli(self) -> str:
        return self.data.get("active_cli")

    @active_cli.setter
    def active_cli(self, value: str) -> None:
        self.data["active_cli"] = value
        self.save()
        self.logger.debug(f"Set active cli to {value}")

    @property
    def active_bootstrap(self) -> str:
        return self.data.get("active_bootstrap", "")

    @active_bootstrap.setter
    def active_bootstrap(self, value: str) -> None:
        self.data["active_bootstrap"] = value
        self.save()
        self.logger.debug(f"Set active bootstrap to {value}")

    @property
    def active_hypervisor(self) -> str:
        return self.data.get("active_hypervisor", "")

    @active_hypervisor.setter
    def active_hypervisor(self, value: str) -> None:
        self.data["active_hypervisor"] = value
        self.save()
        self.logger.debug(f"Set active hypervisor to {value}")

    @property
    def active_inference_client(self) -> str:
        return self.data.get("active_inference_client", None)

    @active_inference_client.setter
    def active_inference_client(self, value: str) -> None:
        self.data["active_inference_client"] = value
        self.save()
        self.logger.debug(f"Set active inference client to {value}")

    @property
    def inference_url(self) -> str:
        return self.data.get("inference_url", "")

    @inference_url.setter
    def inference(self, value: str) -> None:
        self.data["inference_url"] = value
        self.save()
        self.logger.debug(f"Set inference URL to {value}")

    @property
    def posthog_host(self) -> str:
        return self.data.get("ph_h")

    @posthog_host.setter
    def posthog_host(self, value: str):
        self.data["ph_h"] = value
        self.save()
        self.logger.debug(f"Set posthog_host to {value}")

    @property
    def posthog_did(self):
        return self.data.get("ph_did")

    @posthog_did.setter
    def posthog_did(self, value: str) -> str:
        self.data["ph_did"]
        self.save()
        self.logger.debug(f"Set posthog_did to {value}")

    @property
    def metrics_reporting(self):
        return self.data.get("metrics_reporting")

    @metrics_reporting.setter
    def metrics_reporting(self, value: bool):
        self.data["metrics_reporting"] = value
        self.save()
        self.logger.debug(f"Set metrics_reporting to {value}")

    @property
    def core_config(self):
        return {
            "active_bootstrap": self.active_bootstrap,
            "active_hypervisor": self.active_hypervisor,
            "active_inference_client": self.active_inference_client,
            "active_model": self.active_model,
            "active_cli": self.active_cli,
            "inference_url": self.inference_url,
            "metrics_reporting": self.metrics_reporting,
        }

    def __getitem__(self, key: str) -> Any:
        return self.data.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        self.data[key] = value
        self.save()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    config = Config()
    print(f"Active model: {config.active_model}")
    config.active_model = "2025-03-27"
    print(f"Updated active model: {config.active_model}")
