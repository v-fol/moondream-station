import requests
from pathlib import Path
from typing import Optional


class ManualManager:
    def __init__(self, config, manifest_manager):
        self.config = config
        self.manifest_manager = manifest_manager
        self.cache_dir = Path(config.config_dir) / "cache"
        self.cache_file = self.cache_dir / "manual.md"

    def get_manual(self) -> Optional[str]:
        """Fetch manual from URL or cache"""
        # Try to get manual URL from manifest
        manual_url = self._get_manual_url()

        if manual_url:
            # Try to fetch from URL first
            manual_content = self._fetch_from_url(manual_url)
            if manual_content:
                self._save_to_cache(manual_content)
                return manual_content

        # Fall back to cache
        return self._load_from_cache()

    def _get_manual_url(self) -> Optional[str]:
        """Get manual URL from manifest"""
        manifest = self.manifest_manager.get_manifest()
        if not manifest:
            return None

        # Check if manual_url is a direct attribute
        if hasattr(manifest, 'manual_url'):
            return manifest.manual_url

        # Check in the raw dict
        manifest_dict = manifest.dict() if hasattr(manifest, 'dict') else {}
        return manifest_dict.get('manual_url')

    def _fetch_from_url(self, url: str) -> Optional[str]:
        """Fetch manual content from URL"""
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.text
        except Exception:
            return None

    def _save_to_cache(self, content: str):
        """Save manual content to cache"""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.cache_file.write_text(content)
        except Exception:
            pass

    def _load_from_cache(self) -> Optional[str]:
        """Load manual from cache"""
        try:
            if self.cache_file.exists():
                return self.cache_file.read_text()
        except Exception:
            pass
        return None