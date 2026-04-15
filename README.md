# OPD-Vertex

Local-first outpatient department platform built with FastAPI, MySQL, MongoDB, Faster-Whisper, and a single local LLM: `qwen3:8b` through Ollama.

## Stack

- Python 3.12, FastAPI, Jinja2, Uvicorn
- MySQL 8.4 for approved operational data
- MongoDB 7 for prompts, transcripts, and AI draft artifacts
- Faster-Whisper via the `whisper_api` sidecar
- Ollama with `qwen3:8b` for transcript normalization, report generation, and suggestive review

## Architecture

```text
presentation -> application -> domain -> infrastructure
```

- Routes call application services only.
- Application services orchestrate workflow and persistence.
- Domain models define stable DTOs and ports.
- Infrastructure contains replaceable adapters for SQL, MongoDB, Faster-Whisper, Ollama, and startup bootstrap tasks.

## Project Structure

```text
app/
  api/                   FastAPI routes and dependency wiring
  application/           Use-case orchestration services
  domain/                DTOs, enums, repository contracts, service ports
  infrastructure/
    ai/llm/              Ollama client and Qwen3 adapters
    ai/transcription/    Faster-Whisper client adapter
    bootstrap/           Startup prompt and demo-data seeders
    db/sql/              SQLAlchemy tables and SQL repositories
    db/mongo/            Mongo repositories and prompt seed helpers
    persistence/         In-memory repositories for mock/test mode
  templates/             Jinja2 templates
  static/                CSS and JavaScript
whisper_api/             Faster-Whisper HTTP sidecar
alembic/                 SQL migrations
```

## Local Ollama Setup

This project expects a local Ollama instance exposing an HTTP API on port 11434 and the model `qwen3:8b`.

### Windows (recommended)

1. Install Ollama.

If you have `winget`:

```powershell
winget install -e --id Ollama.Ollama
```

If `winget` is not available, install Ollama manually from `https://ollama.com/download`.

2. Start Ollama.

On Windows, the installer typically runs Ollama in the background after install. If it is not running, start the Ollama app from the Start menu.

3. Pull the required model:

```bash
ollama pull qwen3:8b
```

4. Quick sanity check (model responds):

```bash
ollama run qwen3:8b "Say 'ready' and stop."
```

### macOS/Linux

1. Install Ollama from `https://ollama.com/download`.
2. Pull the required model:

```bash
ollama pull qwen3:8b
```

3. Start Ollama:

```bash
ollama serve
```

4. Verify the model is available:

```bash
ollama list
```

### Verify From This App

Once the backend is running, check:

```bash
curl http://127.0.0.1:8000/llm/health
```

You want `healthy: true` and `ollama_reachable: true`.

## Environment Variables

Copy `.env.example` to `.env` and adjust only what you need.

Note: `docker compose` reads `.env` automatically (and this repo also loads `.env` via FastAPI settings), so keeping a real `.env` file is the simplest local workflow.

Important variables:

- `LOCAL_LLM_ENDPOINT` default: `http://localhost:11434`
- `LLM_MODEL_NAME` default: `qwen3:8b`
- `LLM_TEMPERATURE` default: `0.2`
- `LLM_MAX_TOKENS` default: `2200`
- `OLLAMA_TIMEOUT_SECONDS` default: `120`
- `OLLAMA_MAX_RETRIES` default: `2`
- `SEED_PROMPTS_ON_STARTUP` default: `true`
- `SEED_MOCK_CONSULTATIONS_ON_STARTUP` default: `false`
- `USE_MOCK_ADAPTERS` set to `false` to use MySQL, MongoDB, Faster-Whisper, and Ollama

`LLM_MODEL_NAME` is intentionally restricted to `qwen3:8b`.

## Startup Bootstrap

When `USE_MOCK_ADAPTERS=false`, the app can bootstrap MongoDB and SQL data at startup through dedicated infrastructure seeders.

Prompt bootstrap:

- controlled by `SEED_PROMPTS_ON_STARTUP`
- seeds `llm_prompts` automatically
- uses idempotent overwrite/upsert logic by `_id`
- logs whether each prompt was inserted, updated, or skipped

Mock consultation bootstrap:

- controlled by `SEED_MOCK_CONSULTATIONS_ON_STARTUP`
- seeds one demo doctor, four demo patients, four consultations in SQL, and matching `consultation_documents` in MongoDB
- provides synthetic transcript cases for normalization, generation, suggestive review, review loading, and approval projection

## Run Locally

Start infrastructure first:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
uvicorn app.main:app --reload
docker compose up mysql mongo whisper
```
Open http://localhost:8000
Then run the backend on the host machine:

## Demo Credentials
| Role | Email | Password |
|---|---|---|
| Doctor | `doctor@example.local` | `password` |
| Admin | `admin@example.local` | `password` |
| Patient | `giulia@example.local` | `password` |
| Patient | `marco@example.local` | `password` |

```bash
set USE_MOCK_ADAPTERS=false
set SEED_PROMPTS_ON_STARTUP=true
set SEED_MOCK_CONSULTATIONS_ON_STARTUP=true
uvicorn app.main:app --reload
```

Running the backend on the host is the simplest way to reach local Ollama at `http://localhost:11434`.

## Run with Docker

This repo supports a fully containerized setup, including Ollama.

1. Start Ollama and pull the model (stored in a persistent Docker volume):

```bash
docker compose up -d ollama
docker compose exec -T ollama ollama pull qwen3:8b
```

2. Start the rest of the stack:

```bash
docker compose up -d --build
```

### Docker Smoke Test (LLM + Report)

After the stack is up:

```bash
curl http://127.0.0.1:8000/llm/health
curl -X POST http://127.0.0.1:8000/review/4101/generate-report
```

If `/llm/health` reports Ollama unreachable or the model missing, the app container will fail report generation.

## Prompt Storage

Prompt definitions are stored in MongoDB `llm_prompts`.

Manual prompt seeding remains available:

```bash
python -m app.infrastructure.db.mongo.seeds
```

Seeded prompt IDs:

- `transcript_normalization_v1`
- `clinical_report_generation_v2`
- `suggestive_mode_v2`

## Seeded Demo Consultations

When `SEED_MOCK_CONSULTATIONS_ON_STARTUP=true`, the app seeds:

- `4101`: clean happy-path consultation
- `4102`: noisy ASR transcript with recoverable errors
- `4103`: medication and allergy conflict case for suggestive review
- `4104`: sparse consultation with many missing fields

These are synthetic academic/demo records only.

## Implemented AI Workflow

1. Faster-Whisper stores the raw transcript in `consultation_documents`.
2. `POST /review/{consultation_id}/generate-report`:
   - loads the transcript from MongoDB
   - normalizes and reorders it with Qwen3
   - generates a structured English medical report with Qwen3
   - stores the draft in MongoDB `generated_documents`
3. `POST /review/{consultation_id}/suggestive-review`:
   - runs a second-pass Qwen3 safety review
   - stores the suggestive output in MongoDB
4. `POST /review/{consultation_id}/approve`:
   - keeps the reviewed draft in MongoDB
   - projects the approved prescription data into SQL
   - marks the consultation approved

No AI draft is projected into SQL before approval.

## API Endpoints

### Transcription

- `POST /transcriptions/session/start`
- `GET /transcriptions/session/{session_id}/results`
- `POST /transcriptions/session/{session_id}/complete`
- `POST /transcriptions/save-transcription`

### Review and AI Drafting

- `GET /review/{consultation_id}`
- `POST /review/{consultation_id}/generate-report`
- `POST /review/{consultation_id}/regenerate`
- `POST /review/{consultation_id}/suggestive-review`
- `POST /review/{consultation_id}/approve`
- `POST /review/{consultation_id}/reject`

### Local LLM Health

- `GET /llm/health`

## Endpoint Examples

Generate a report:

```bash
curl -X POST http://127.0.0.1:8000/review/4101/generate-report
```

Run suggestive review:

```bash
curl -X POST http://127.0.0.1:8000/review/4103/suggestive-review
```

Regenerate the draft:

```bash
curl -X POST http://127.0.0.1:8000/review/4102/regenerate
```

Approve and project to SQL:

```bash
curl -X POST http://127.0.0.1:8000/review/4101/approve
```

Check local Ollama health:

```bash
curl http://127.0.0.1:8000/llm/health
```

## Troubleshooting

- `Configured model 'qwen3:8b' is not available in Ollama.`
  Run `ollama pull qwen3:8b`.
- `Ollama request failed`
  Make sure `ollama serve` is running and `LOCAL_LLM_ENDPOINT` is correct.
- Docker backend cannot reach Ollama
  Keep Ollama on the host and use `host.docker.internal:11434`.
- `Prompt '...' is missing from llm_prompts`
  Enable `SEED_PROMPTS_ON_STARTUP=true` or run `python -m app.infrastructure.db.mongo.seeds`.
- Demo consultations are missing
  Enable `SEED_MOCK_CONSULTATIONS_ON_STARTUP=true` and restart the backend.
- Report generation fails with malformed model output
  The backend performs one controlled JSON repair pass with the same Qwen3 model. Persistent failures usually mean Ollama is overloaded or the stored prompt documents were edited incorrectly.

## Tests

```bash
pytest
```
