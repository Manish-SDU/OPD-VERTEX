# OPD-Vertex

Local-first outpatient department platform. FastAPI + MySQL + MongoDB + local LLM.

## Stack

- Python 3.12, FastAPI, Jinja2, Uvicorn
- MySQL 8.4 (SQL) + MongoDB 7 (NoSQL)
- SQLAlchemy + Alembic (migrations)
- PyMongo
- Bcrypt (auth)
- Pydantic Settings

## Project Structure

```
app/
  api/           → FastAPI routes + dependency wiring
  application/   → Use-case services
  domain/        → Pydantic models, enums, repository contracts (ABCs)
  infrastructure/
    db/sql/      → SQLAlchemy ORM models + connection + repository stubs
    db/mongo/    → PyMongo connection + collection names + repository stubs
    ai/          → LLM + transcription adapter stubs
    persistence/ → In-memory mock repositories (for dev/testing)
  templates/     → Jinja2 HTML
  static/        → CSS/JS
alembic/         → SQL migration scripts
```

## Quick Start

```bash
pip install -e .[dev]
uvicorn app.main:app --reload
```

Open http://localhost:8000

## Demo Credentials

| Role | Email | Password |
|---|---|---|
| Doctor | `doctor@example.local` | `password` |
| Admin | `admin@example.local` | `password` |
| Patient | `giulia@example.local` | `password` |
| Patient | `marco@example.local` | `password` |

## Run with Docker

```bash
docker compose up --build
```
