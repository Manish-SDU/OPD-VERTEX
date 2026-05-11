FROM python:3.12-slim

WORKDIR /workspace

COPY pyproject.toml README.md alembic.ini ./
COPY app ./app
COPY alembic ./alembic
COPY .env.example ./.env.example
COPY entrypoint.sh ./entrypoint.sh

RUN pip install --no-cache-dir -e .[dev] \
    && chmod +x /workspace/entrypoint.sh

EXPOSE 8000

CMD ["/workspace/entrypoint.sh"]
