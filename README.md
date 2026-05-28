# OPD-Vertex

Local-first outpatient department system. Doctors record consultations via voice, the system transcribes speech in real time with Faster-Whisper (large-v3), generates structured clinical reports with a local LLM (Qwen3:8b via Ollama), and lets doctors review and approve before committing anything to the database.

No data ever leaves the machine. Everything — transcription, LLM inference, email — runs locally inside Docker containers.

---

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| **Docker Desktop** | Latest | Must be running before any command below |
| **NVIDIA GPU + drivers** | Optional | Whisper runs on GPU if available, CPU otherwise |
| **Git** | Any | Only needed if cloning; skip if unzipping the archive |

> **Windows users:** Docker Desktop must be running (the whale icon in the system tray). If you have an NVIDIA GPU, make sure the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) is installed for GPU acceleration.

---

## Setup — From Zero to Running

### 1. Get the project

```bash
# Either unzip the archive, or clone:
git clone <repo-url>
cd OPD-VERTEX
```

### 2. Create the environment file

```bash
cp .env.example .env
```

The defaults in `.env.example` work out of the box — no changes required.

### 3. Build and start all containers

```bash
docker compose up -d --build
```

This starts 6 services: **app**, **whisper**, **mysql**, **mongodb**, **ollama**, **mailhog**.

> **First-time build:** The Whisper container downloads the `large-v3` model (~3 GB) during the build. This takes a few minutes depending on your internet connection. Subsequent builds are instant (model is cached).

### 4. Pull the LLM model (first time only)

```bash
docker compose exec ollama ollama pull qwen3:8b
```

This downloads the Qwen3 8B model (~5 GB). Only needed once — it is stored in a Docker volume and persists across restarts.

### 5. Open the app

| Service | URL | Purpose |
|---|---|---|
| **Main application** | http://localhost:8000 | Doctor / admin / patient UI |
| **MailHog inbox** | http://localhost:8025 | Catch-all email inbox (prescriptions, notifications) |

That's it. The app is ready.

---

## Credentials

All accounts use the password: **`password`**

### Staff

| Role | Email | Name |
|---|---|---|
| Doctor | `doctor@example.local` | Ada Demo |
| Admin | `admin@example.local` | — |

### Patients

| Email | Name |
|---|---|
| `giulia@example.local` | Giulia Rossi |
| `marco@example.local` | Marco Bianchi |
| `ava.miller@example.local` | Ava Miller |
| `noah.perez@example.local` | Noah Perez |
| `mia.nguyen@example.local` | Mia Nguyen |
| `luca.reed@example.local` | Luca Reed |

> The application ships with pre-seeded consultations and data so you can explore all features immediately after login.

---

## Core Features & How to Test Them

### As a Doctor (`doctor@example.local`)

1. **Start a consultation** — go to Consultations → New Consultation, select a patient, click Start Recording and speak into the microphone. Live transcription appears in real time.
2. **Generate clinical report** — after stopping the recording, click "Generate Report". The LLM (Qwen3:8b) reads the transcript and produces a structured clinical note.
3. **Suggestive Review** — a second-pass AI safety review flags potential issues in the report.
4. **Approve & issue prescription** — review the draft, edit if needed, approve. A PDF prescription is generated and emailed to the patient.
5. **View patient history** — past consultations, prescriptions, and reports are all accessible per patient.

### As an Admin (`admin@example.local`)

- Manage staff accounts, patients, appointments, and system configuration.
- View audit logs of all clinical actions.

### As a Patient (`giulia@example.local`)

- View personal consultation history and prescriptions.
- Book appointments.

### Email (MailHog)

All outgoing emails (prescription delivery, notifications) are caught by MailHog — open http://localhost:8025 to see them. No real SMTP server is required.

---

## Architecture

```
Browser
  │
  ▼
app (FastAPI + Jinja2)  :8000
  ├── MySQL 8.4          :3306   — patients, staff, appointments, prescriptions
  ├── MongoDB 7          :27017  — transcripts, clinical notes, generated documents
  ├── Ollama (Qwen3:8b)  :11434  — local LLM for report generation
  └── Whisper sidecar    :8001   — real-time speech-to-text (Faster-Whisper large-v3)
                                   runs on NVIDIA GPU if available, CPU otherwise
```

**Clean Architecture** — Domain → Application → Infrastructure → API. No AI output is committed to the database until a doctor explicitly approves it.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, Uvicorn |
| Frontend | Jinja2 templates, HTML5, CSS3, Vanilla JS |
| Audio capture | Web Audio API (PCM16 streaming) |
| Relational DB | MySQL 8.4 + SQLAlchemy 2 + Alembic |
| Document DB | MongoDB 7 + pymongo |
| Transcription | Faster-Whisper large-v3 (ctranslate2, CUDA 12.8.1) |
| LLM | Ollama + Qwen3:8b |
| PDF | ReportLab |
| Email | smtplib + MailHog (dev) |
| Auth | JWT cookies + bcrypt |
| Containers | Docker + Docker Compose |
| GPU | NVIDIA CUDA 12.8.1 + cuDNN (RTX series, including RTX 5070 Blackwell) |
| Testing | pytest (284+ tests), Ruff (linter + formatter) |

---

## Stopping and Restarting

```bash
# Stop all containers (data is preserved in Docker volumes)
docker compose down

# Start again (no rebuild needed)
docker compose up -d

# Full reset — deletes all data and volumes
docker compose down -v
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Containers not starting | Make sure Docker Desktop is running |
| `qwen3:8b` not available / LLM errors | Run `docker compose exec ollama ollama pull qwen3:8b` |
| Whisper not transcribing | Check `docker compose logs whisper` — it should say `Model initialized model=large-v3` |
| No GPU acceleration | Install NVIDIA Container Toolkit, then `docker compose up -d --build whisper` |
| Email not appearing | Open http://localhost:8025 (MailHog) |
| Port already in use | Stop any local MySQL (port 3306) or MongoDB (port 27017) running on the host |
| Blank page / 500 error | Run `docker compose logs app` to see the error |

---

## Environment Variables

The `.env` file (copied from `.env.example`) controls all runtime behaviour. Key variables:

| Variable | Default | Description |
|---|---|---|
| `USE_MOCK_ADAPTERS` | `true` | Uses in-memory repositories with seeded demo data — no real DB writes |
| `WHISPER_MODEL_NAME` | `large-v3` | Whisper model size (`base`, `small`, `medium`, `large-v3`) |
| `LLM_MODEL_NAME` | `qwen3:8b` | Ollama model name |
| `SMTP_HOST` / `SMTP_PORT` | `mailhog` / `1025` | Email server (MailHog is automatic in Docker) |
| `SECRET_KEY` | `pass` | JWT signing key — change in production |

> With `USE_MOCK_ADAPTERS=true` (the default), the app uses pre-seeded in-memory data. All features work, including AI transcription and report generation. Set to `false` only if you want persistent SQL/Mongo writes.

---

## Running Tests

```bash
# Inside Docker
docker compose exec app pytest

# Locally (requires .venv)
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e .[dev]
pytest
```
