FROM python:3.12-slim

WORKDIR /workspace

COPY pyproject.toml README.md alembic.ini ./
COPY app ./app
COPY alembic ./alembic
COPY .env.example ./.env.example

RUN pip install --no-cache-dir -e .[dev]

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
