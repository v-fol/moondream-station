#!/bin/bash
set -e

echo "Setting pod to terminate after 12 hours..."
nohup bash -c "sleep 12h; runpodctl remove pod $RUNPOD_POD_ID" &>/dev/null &

echo "Installing main requirements..."
pip install -r /workspace/moondream-station/requirements.txt

echo "Installing backend requirements..."
pip install -r /workspace/moondream-station/backends/mds_backend_0/requirements.txt

echo "Starting API server..."
python3 /workspace/moondream-station/api_launcher.py
