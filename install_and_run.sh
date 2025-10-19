#!/bin/bash
set -e

echo "Cloning moondream-station..."
git clone https://github.com/v-fol/moondream-station.git
cd moondream-station

echo "Installing main requirements..."
pip install -r requirements.txt

echo "Installing backend requirements..."
pip install -r backends/mds_backend_0/requirements.txt

echo "Starting API server..."
python3 api_launcher.py
