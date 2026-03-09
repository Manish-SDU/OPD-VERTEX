# OPD-Vertex

OPD-Vertex is a local-first scaffold for a privacy-preserving outpatient department platform. This repository intentionally contains architectural scaffolding, mock adapters, route stubs, templates, tests, and documentation, but not the real database layer, AI pipeline, PDF rendering, or production authentication.

## Goals

- Boot a clean FastAPI project aligned with layered architecture.
- Keep AI, persistence, PDF, and email capabilities replaceable through explicit contracts.
- Provide enough placeholder behavior for teammates to start implementing bounded contexts in parallel.

## Stack

- Python 3.12
- FastAPI + Jinja2 + Uvicorn
- Pydantic Settings
- Docker / Docker Compose
- pytest
- MySQL and MongoDB as future persistence targets

## What Is Scaffolded

- Server-rendered dashboard, auth, patients, consultations, review, prescriptions, and admin pages
- Domain contracts and DTOs for the main healthcare workflow
- In-memory repositories and mock services for boot-time/demo behavior
- Config management, logging bootstrap, docs, tests, and dev tooling placeholders

## What Is Intentionally Not Implemented

- Real MySQL or MongoDB persistence
- Secure authentication, sessions, or RBAC enforcement
- Real audio transcription, local LLM orchestration, PDF generation, or email sending
- Production-ready validation, observability, or deployment hardening

## Repository Structure

- `app/api`: FastAPI routers and dependency wiring
- `app/application`: application services orchestrating use cases
- `app/domain`: entities, DTOs, enums, and service/repository contracts
- `app/infrastructure`: mock adapters, placeholder persistence, and future integration zones
- `app/templates` and `app/static`: server-rendered UI scaffold
- `app/tests`: smoke, integration, and unit tests
- `docs`: architecture, module notes, contribution guide, and handover

## Run Locally

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e .[dev]
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Docker

```bash
docker compose up --build
```

The compose file starts `app`, `mysql`, and `mongo`. The application still uses in-memory adapters by default.

## How To Switch Later To Real Persistence

1. Implement MySQL repositories under `app/infrastructure/db/sql/repositories`.
2. Implement Mongo repositories under `app/infrastructure/db/mongo/repositories`.
3. Update dependency wiring in `app/api/deps.py` to choose real adapters from settings.
4. Add Alembic revisions and seed scripts.

## Recommended Next Implementation Order

1. Persistence adapters and schema migrations.
2. Authentication/session hardening and RBAC hooks.
3. Transcription and local LLM integrations.
4. Review approval workflow and prescription finalization.
5. PDF generation and secure email delivery.
