#!/usr/bin/env python3
import sys
from pathlib import Path
import uvicorn

sys.path.insert(0, str(Path(__file__).parent))

from moondream_station.core.config import ConfigManager
from moondream_station.core.manifest import ManifestManager
from moondream_station.core.rest_server import RestServer
from moondream_station.core.analytics import Analytics
from moondream_station.session import SessionState

# Initialize
config = ConfigManager()
manifest_manager = ManifestManager(config)
manifest_manager.load_manifest("./local_manifest.json")

# Get default model
model_name = manifest_manager.get_available_default_model()
config.set("current_model", model_name)

# Setup server
analytics = Analytics(config, manifest_manager)
session_state = SessionState()
server = RestServer(config, manifest_manager, session_state, analytics)

# Start inference service
if not server.inference_service.start(model_name):
    print("Failed to start inference service")
    sys.exit(1)

# Pre-load model into memory before API becomes available
print("Pre-loading model into memory...")
backend_module = server.inference_service.worker_backends[0]
get_model_service = getattr(backend_module, 'get_model_service')
model_service = get_model_service()
print(f"Model loaded: {model_service.model_name}")
print(f"Device: {model_service.device}")

# Run FastAPI directly with uvicorn
uvicorn.run(server.app, host="0.0.0.0", port=2020, log_level="info")
