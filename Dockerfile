FROM python:3.12-slim as builder

WORKDIR /workspace

COPY pyproject.toml README.md ./
COPY app ./app

# Install dependencies
RUN pip install --no-cache-dir -e .[dev]

# Set HuggingFace cache directory
ENV HF_HOME=/workspace/app/models
RUN mkdir -p /workspace/app/models

# Download Faster-Whisper models during build
COPY app/scripts/download_whisper_model.py ./app/scripts/
RUN python app/scripts/download_whisper_model.py


FROM python:3.12-slim

WORKDIR /workspace

COPY pyproject.toml README.md ./
COPY app ./app
COPY alembic ./alembic
COPY .env.example ./.env.example

RUN pip install --no-cache-dir -e .[dev]

# Set HuggingFace cache to persistent location
ENV HF_HOME=/workspace/app/models

# Copy models from builder stage
COPY --from=builder /workspace/app/models /workspace/app/models

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
