#!/usr/bin/env bash
set -euo pipefail

# Configure huggingface token if provided
if [[ -n "${HF_TOKEN:-}" ]]; then
  mkdir -p /root/.cache/huggingface
  mkdir -p /root/.huggingface
  echo "machine huggingface.co" > /root/.huggingface/token
  echo "  login hf_user" >> /root/.huggingface/token
  echo "  password ${HF_TOKEN}" >> /root/.huggingface/token
  chmod 600 /root/.huggingface/token
  # Also store token in CLI config for completeness
  echo "{""token"":""${HF_TOKEN}""}" > /root/.cache/huggingface/token
fi

# Ensure environment variables are respected by server
export HF_HUB_ENABLE_HF_TRANSFER=${HF_HUB_ENABLE_HF_TRANSFER:-0}
export SERVICE_HOST=${SERVICE_HOST:-0.0.0.0}
export SERVICE_PORT=${SERVICE_PORT:-2020}

# Pre-create moondream-station config to avoid interactive prompts
mkdir -p /root/.moondream-station
cat > /root/.moondream-station/config.json <<EOF
{
  "current_model": null,
  "service_port": ${SERVICE_PORT},
  "models_dir": "/root/.moondream-station/models",
  "update_endpoint": "https://api.github.com/repos/m87/moondream-station/releases/latest",
  "service_host": "${SERVICE_HOST}",
  "auto_start": true,
  "log_level": "INFO",
  "inference_workers": 1,
  "inference_max_queue_size": 10,
  "inference_timeout": 60.0,
  "logging": false
}
EOF

# Force default model to Moondream3 when available in manifest
export MDS_MANIFEST="${MDS_MANIFEST:-/app/production_manifest.json}"

echo "Starting Moondream Station with manifest: ${MDS_MANIFEST}"

# Start the CLI non-interactively – it will auto-load manifest, pick default model, start server
exec python3 -m moondream_station.cli --manifest "${MDS_MANIFEST}"

