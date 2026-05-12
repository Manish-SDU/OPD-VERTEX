# OPD-Vertex

Local-first outpatient department system. Doctors record consultations via voice, the system transcribes with Faster-Whisper, generates structured clinical reports with a local LLM (Qwen3:8b), and lets doctors review and approve before committing to SQL.

## Stack

| Layer | Technology |
|---|---|
| API & UI | FastAPI, Jinja2, Uvicorn |
| Relational DB | MySQL 8.4 |
| Document DB | MongoDB 7 |
| Transcription | Faster-Whisper (sidecar) |
| LLM | Ollama + qwen3:8b |
| Email | SMTP (MailHog in dev, SendGrid/Gmail in prod) |

## Quick Start

### Mock mode (no external services needed)

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -e .[dev]
uvicorn app.main:app --reload
```

Open http://localhost:8000 and use the demo credentials below.

### Full stack with Docker

```bash
# 1. Start everything
docker compose up -d --build

# 2. Pull the LLM model (first time only, ~5 GB)
docker compose exec ollama ollama pull qwen3:8b

# 3. Run migrations
docker compose exec app alembic upgrade head
```

App: http://localhost:8000 · MailHog inbox: http://localhost:8025

## Environment

Copy `.env.example` to `.env`. Key variables:

| Variable | Default | Notes |
|---|---|---|
| `USE_MOCK_ADAPTERS` | `true` | Set `false` for real MySQL/Mongo/Ollama |
| `LOCAL_LLM_ENDPOINT` | `http://localhost:11434` | Ollama URL |
| `WHISPER_API_URL` | `http://localhost:8001` | Whisper sidecar |
| `LLM_MODEL_NAME` | `qwen3:8b` | Only accepted value |
| `SMTP_HOST` / `SMTP_PORT` | `localhost` / `1025` | See [docs/email-setup.md](docs/email-setup.md) |

## Credentials

Mock mode: doctor `doctor@example.local` / `password`; admin `admin@example.local` / `password`.

Real seeded mode: doctor `harper.cole@example.local` / `password`; patients like `ava.miller@example.local` / `password`.

## AI Workflow

1. Browser mic → Faster-Whisper → raw transcript saved in MongoDB
2. `POST /review/{id}/generate-report` → Qwen3 normalises transcript → generates structured report → saved as draft
3. `POST /review/{id}/suggestive-review` → second-pass safety review
4. `POST /review/{id}/approve` → prescription projected into SQL, consultation closed

No AI output touches SQL until the doctor approves.

## Tests

```bash
pytest                                    # all 310 tests
pytest app/tests/unit/                    # unit only
pytest app/tests/integration/             # integration
pytest app/tests/benchmarks/             # benchmarks
python scripts/generate_test_graphs.py   # benchmark HTML report → reports/
```

See [docs/testing.md](docs/testing.md) for the full breakdown.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `qwen3:8b` not available | `ollama pull qwen3:8b` |
| Ollama unreachable | Make sure `ollama serve` is running |
| Docker can't reach host Ollama | Use `LOCAL_LLM_ENDPOINT=http://host.docker.internal:11434` |
| Missing demo consultations | Set `SEED_MOCK_CONSULTATIONS_ON_STARTUP=true` and restart |
| Email not delivered | See [docs/email-setup.md](docs/email-setup.md) |
