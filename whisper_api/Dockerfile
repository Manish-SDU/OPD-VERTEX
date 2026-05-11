FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY pipeline.py server.py ./

ENV WHISPER_MODEL=large-v3 WHISPER_DEVICE=cpu WHISPER_COMPUTE_TYPE=int8 WHISPER_PORT=8001
EXPOSE 8001
CMD ["python", "server.py"]
