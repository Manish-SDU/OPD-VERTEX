FROM python:3.12-slim AS builder

WORKDIR /whisper-api

COPY whisper_api/pyproject.toml ./
COPY whisper_api/ ./whisper_api/

# Install dependencies
RUN pip install --no-cache-dir -e .

# Set HuggingFace cache directory
ENV HF_HOME=/whisper-api/models
RUN mkdir -p /whisper-api/models

# Download Faster-Whisper models during build
COPY app/scripts/download_whisper_model.py ./app/scripts/
RUN python app/scripts/download_whisper_model.py


FROM python:3.12-slim

WORKDIR /whisper-api

COPY whisper_api/pyproject.toml ./
COPY whisper_api/ ./whisper_api/

RUN pip install --no-cache-dir -e .

# Set HuggingFace cache to persistent location
ENV HF_HOME=/whisper-api/models

# Copy models from builder stage
COPY --from=builder /whisper-api/models /whisper-api/models

EXPOSE 8001

CMD ["python", "-m", "whisper_api.main"]
