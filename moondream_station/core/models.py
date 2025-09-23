import platform
from typing import List, Dict, Optional
from .manifest import ModelInfo


class ModelManager:
    def __init__(self, config, manifest_manager=None):
        self.config = config
        self.manifest_manager = manifest_manager
    
    def list_models(self) -> List[str]:
        """Get list of available model names"""
        if not self.manifest_manager:
            return []
        return list(self.manifest_manager.get_models().keys())
    
    def get_model(self, name: str) -> Optional[ModelInfo]:
        """Get model info by name"""
        if not self.manifest_manager:
            return None
        models = self.manifest_manager.get_models()
        return models.get(name)
    
    def get_active_model(self) -> Optional[ModelInfo]:
        """Get currently active model"""
        current_model = self.config.get("current_model")
        if current_model:
            return self.get_model(current_model)
        return None
    
    def switch_model(self, name: str, display=None) -> bool:
        """Switch to a different model"""
        if not self.manifest_manager:
            return False

        models = self.manifest_manager.get_models()
        if name not in models:
            return False

        # Check OS compatibility
        model_info = models[name]
        if model_info.supported_os:
            current_os = platform.system().lower()
            if current_os not in model_info.supported_os:
                return False

        # Get backend with spinner for downloading/setup
        if display:
            with display.spinner(f"Setting up {name} backend"):
                backend = self.manifest_manager.get_backend_for_model(name)
        else:
            backend = self.manifest_manager.get_backend_for_model(name)

        if not backend:
            return False

        self.config.set("current_model", name)
        return True
    
    def get_models_info(self) -> Dict[str, ModelInfo]:
        """Get all models info"""
        if not self.manifest_manager:
            return {}
        return self.manifest_manager.get_models()

    def is_model_supported(self, name: str) -> tuple[bool, str]:
        """Check if a model is supported, return (is_supported, reason_if_not)"""
        models_info = self.get_models_info()
        if name not in models_info:
            return False, "Model not found"

        model_info = models_info[name]
        manifest = self.manifest_manager.get_manifest() if self.manifest_manager else None
        current_os = platform.system().lower()

        # Check OS compatibility (same logic as display.py)
        if model_info.supported_os and current_os not in model_info.supported_os:
            return False, f"Not supported on {current_os}"

        # Check version compatibility (same logic as display.py)
        if manifest and model_info.backend in manifest.backends:
            backend_info = manifest.backends[model_info.backend]
            if backend_info.min_version:
                try:
                    from .. import __version__
                    from packaging.version import Version
                    if Version(__version__) < Version(backend_info.min_version):
                        return False, f"Requires version {backend_info.min_version} or newer"
                except:
                    pass

        return True, ""