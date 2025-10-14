FROM nvidia/cuda:12.8.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_ENABLE_HF_TRANSFER=0 \
    SERVICE_HOST=0.0.0.0 \
    SERVICE_PORT=2020 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-full python3-venv python3-pip git curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project
COPY . /app

# Install moondream-station + backend requirements
RUN pip3 install --upgrade pip && \
    pip3 install -e . && \
    # Core server deps
    pip3 install -r moondream_station/requirements.txt && \
    # Hugging Face CLI for login automation
    pip3 install "huggingface_hub[cli]" && \
    # Install GPU PyTorch matching CUDA 12.8
    pip3 install --index-url https://download.pytorch.org/whl/cu128 torch torchvision torchaudio && \
    # Backend deps (transformers/accelerate/Pillow); keeps installed GPU torch
    pip3 install -r backends/mds_backend_0/requirements.txt

# Expose port
EXPOSE 2020

# Default to local manifest (uses bundled backend code)
ENV MDS_MANIFEST=/app/local_manifest.json

# Allow setting HF token at runtime via env var HF_TOKEN
ENV HF_TOKEN=""

# Entry script handles non-interactive startup
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

