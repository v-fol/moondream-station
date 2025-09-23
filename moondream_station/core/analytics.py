import uuid
import platform
import traceback
import os
from typing import Dict, Any, Optional

import posthog
import requests

posthog.disabled = True  # Start disabled to prevent auto-uploads on import


class Analytics:
    def __init__(self, config_manager, manifest_manager=None):
        self.config = config_manager
        self.manifest_manager = manifest_manager
        self.client = None
        self.has_base_model = False

        if not self.config.get("user_id"):
            self.config.set("user_id", str(uuid.uuid4()))

        self._initialize_posthog()

    def _check_base_model(self):
        """Check if we can access the base model"""
        if not requests:
            self.has_base_model = False
            return

        try:
            hf_token = os.environ.get("HF_TOKEN")
            if hf_token:
                headers = {"Authorization": f"Bearer {hf_token}"}
                response = requests.get(
                    "https://huggingface.co/moondream/moondream3-preview/blob/main/config.json",
                    headers=headers,
                    timeout=2,
                )
                if response.status_code == 200:
                    self.has_base_model = True
                    if self.has_base_model and self.client is None:
                        self._setup_posthog_client()
                    return
        except:
            pass

        try:
            response = requests.get(
                "https://huggingface.co/vikhyatk/moondream2/resolve/main/config.json",
                timeout=2,
            )
            self.has_base_model = response.status_code == 200
        except:
            self.has_base_model = False

        if self.has_base_model and self.client is None:
            self._setup_posthog_client()

    def _initialize_posthog(self):
        """Initialize PostHog with current manifest config"""
        if self.config.get("logging", True):
            analytics_config = self._get_analytics_config()
            if analytics_config:
                self._check_base_model()

                if not self.has_base_model:
                    self.client = None
                    return

                self._setup_posthog_client()

    def _setup_posthog_client(self):
        """Setup PostHog client when we have connectivity"""
        if not self.config.get("logging", True):
            return

        analytics_config = self._get_analytics_config()
        if analytics_config:
            project_key = analytics_config.get("posthog_project_key")
            host = analytics_config.get("posthog_host", "https://app.posthog.com")

            posthog.disabled = False  # Enable now that we have connectivity
            posthog.api_key = project_key
            posthog.host = host
            posthog.enable_exception_autocapture = True
            posthog.debug = False
            posthog.on_error = lambda error, batch: None
            self.client = posthog

    def _get_analytics_config(self):
        if not self.manifest_manager:
            return None

        manifest_data = self.manifest_manager.get_manifest()
        if not manifest_data:
            return None

        if hasattr(manifest_data, "analytics"):
            return getattr(manifest_data, "analytics", None)
        return None

    def track(self, event: str, properties: Optional[Dict[str, Any]] = None):
        if not self.client or not self.config.get("logging", True):
            return

        # Check base model access before trying to upload
        self._check_base_model()
        if not self.has_base_model:
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
            self.client.capture(
                distinct_id=self.config.get("user_id"),
                event=event,
                properties=properties,
            )
        except Exception:
            pass

    def track_api_call(
        self,
        endpoint: str,
        duration: float,
        tokens: int = 0,
        success: bool = True,
        model: str = None,
    ):
        self.track(
            "api_call",
            {
                "endpoint": endpoint,
                "duration_ms": round(duration * 1000),
                "tokens": tokens,
                "success": success,
                "model": model,
            },
        )

    def track_error(self, error_type: str, error_msg: str, context: str = None):
        self.track(
            "error",
            {
                "error_type": error_type,
                "error_message": error_msg,
                "context": context,
                "traceback": traceback.format_exc(),
            },
        )
