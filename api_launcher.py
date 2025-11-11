#!/usr/bin/env python3
import sys
import os
import logging
from pathlib import Path
import uvicorn

sys.path.insert(0, str(Path(__file__).parent))

from moondream_station.core.config import ConfigManager
from moondream_station.core.manifest import ManifestManager
from moondream_station.core.rest_server import RestServer
from moondream_station.core.analytics import Analytics
from moondream_station.session import SessionState

# Configure logging for shutdown monitor visibility
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Initialize
config = ConfigManager()
manifest_manager = ManifestManager(config)
manifest_manager.load_manifest(f"{os.getenv('MDS_MANIFEST_PATH', '/local_manifest.json')}")

# Get default model
model_name = manifest_manager.get_available_default_model()
config.set("current_model", model_name)

# Configure shutdown monitor settings (can be overridden via environment variables)
# SHUTDOWN_MONITOR_ENABLED: "true" or "false" (default: "true")
# SHUTDOWN_CHECK_INTERVAL: seconds between checks (default: 30.0)
# SHUTDOWN_TIMEOUT: seconds idle before shutdown (default: 30.0)
if os.getenv("SHUTDOWN_MONITOR_ENABLED"):
    config.set("shutdown_monitor_enabled", os.getenv("SHUTDOWN_MONITOR_ENABLED").lower() == "true")
if os.getenv("SHUTDOWN_CHECK_INTERVAL"):
    try:
        config.set("shutdown_check_interval", float(os.getenv("SHUTDOWN_CHECK_INTERVAL")))
    except ValueError:
        print(f"Warning: Invalid SHUTDOWN_CHECK_INTERVAL value, using default")
if os.getenv("SHUTDOWN_TIMEOUT"):
    try:
        config.set("shutdown_timeout", float(os.getenv("SHUTDOWN_TIMEOUT")))
    except ValueError:
        print(f"Warning: Invalid SHUTDOWN_TIMEOUT value, using default")

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
