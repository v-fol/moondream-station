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

COPY . /app

EXPOSE 2020

RUN pip install -r requirements.txt && pip install -r backends/mds_backend_0/requirements.txt

CMD ["python3", "api_launcher.py"]

