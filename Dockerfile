FROM pytorch/pytorch:2.8.0-cuda12.9-cudnn9-runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HUB_ENABLE_HF_TRANSFER=0 \
    SERVICE_HOST=0.0.0.0 \
    SERVICE_PORT=2020 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Copy project
COPY . /app

# Expose port
EXPOSE 2020

# Allow setting HF token at runtime via env var HF_TOKEN
ENV HF_TOKEN=""

# Entry script handles non-interactive startup
COPY install_and_run.sh /install_and_run.sh
RUN chmod +x /install_and_run.sh

ENTRYPOINT ["/install_and_run.sh"]

