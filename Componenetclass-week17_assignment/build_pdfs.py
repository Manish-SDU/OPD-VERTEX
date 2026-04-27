"""Build the two assignment PDFs (concise) using fpdf2."""
from __future__ import annotations
from pathlib import Path
from fpdf import FPDF
from PIL import Image

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
DIAG = REPO / "docs" / "diagrams"
SHOTS = REPO / "reports" / "test-screenshots"
OUT = ROOT

AUTHORS = (
    "Aleksandra Kwiatkowska, Gabija Staskeviciute, Gabriele Solazzo, "
    "Luigi Colluto, Manish Raj Moriche, Mats Pete Haertel"
)

NAVY = (12, 38, 76)
ACCENT = (54, 113, 181)
GREY = (110, 110, 115)
LIGHT = (235, 240, 248)
TEXT = (25, 25, 28)


class PDF(FPDF):
    title_text = ""

    def header(self) -> None:
        # Header lives in the top margin (y = 6..14); body starts at y = 16.
        self.set_y(6)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*NAVY)
        self.cell(0, 4, self.title_text, align="L")
        self.set_xy(self.l_margin, 6)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*GREY)
        self.cell(0, 4, "OPD-Vertex  -  Group Assignment", align="R")
        self.set_draw_color(*ACCENT)
        self.set_line_width(0.4)
        self.line(self.l_margin, 12, self.w - self.r_margin, 12)
        self.set_y(16)

    def footer(self) -> None:
        self.set_y(-10)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(*GREY)
        self.cell(0, 4, AUTHORS, align="L")
        self.set_xy(-30, self.get_y())
        self.cell(20, 4, f"p. {self.page_no()}/{{nb}}", align="R")


def h1(pdf: PDF, text: str) -> None:
    pdf.ln(1)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*NAVY)
    pdf.set_fill_color(*LIGHT)
    pdf.cell(0, 6, "  " + text, fill=True)
    pdf.ln(7)


def h2(pdf: PDF, text: str) -> None:
    pdf.ln(0.5)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*ACCENT)
    pdf.cell(0, 4.5, text)
    pdf.ln(5)


def body(pdf: PDF, text: str, size: float = 9) -> None:
    pdf.set_font("Helvetica", "", size)
    pdf.set_text_color(*TEXT)
    pdf.multi_cell(0, 4, text)
    pdf.ln(0.5)


def bullets(pdf: PDF, items: list[str], size: float = 8.8) -> None:
    pdf.set_font("Helvetica", "", size)
    pdf.set_text_color(*TEXT)
    width = pdf.w - pdf.l_margin - pdf.r_margin
    for it in items:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(width, 3.9, "  -  " + it)
    pdf.ln(0.5)


def fitted_image(pdf: PDF, path: Path, max_w: float, max_h: float, caption: str | None = None) -> None:
    with Image.open(path) as im:
        iw, ih = im.size
    ratio = min(max_w / iw, max_h / ih)
    w = iw * ratio
    h = ih * ratio
    x = (pdf.w - w) / 2
    pdf.image(str(path), x=x, y=pdf.get_y(), w=w, h=h)
    pdf.ln(h + 1)
    if caption:
        pdf.set_font("Helvetica", "I", 7.5)
        pdf.set_text_color(*GREY)
        pdf.cell(0, 3.5, caption, align="C")
        pdf.ln(4)


def two_col_table(pdf: PDF, headers: tuple[str, str], rows: list[tuple[str, str]],
                  col_w: tuple[float, float], font_size: float = 8) -> None:
    pdf.set_font("Helvetica", "B", font_size)
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(col_w[0], 5, " " + headers[0], fill=True)
    pdf.cell(col_w[1], 5, " " + headers[1], fill=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", "", font_size)
    pdf.set_text_color(*TEXT)
    for a, b in rows:
        x0, y0 = pdf.get_x(), pdf.get_y()
        pdf.set_xy(x0, y0)
        pdf.multi_cell(col_w[0], 4, " " + a, border=0)
        y1 = pdf.get_y()
        pdf.set_xy(x0 + col_w[0], y0)
        pdf.multi_cell(col_w[1], 4, " " + b, border=0)
        y2 = pdf.get_y()
        pdf.set_y(max(y1, y2))
    pdf.ln(1)


def three_col_table(pdf: PDF, headers: tuple[str, str, str], rows: list[tuple[str, str, str]],
                    col_w: tuple[float, float, float], font_size: float = 7.6) -> None:
    pdf.set_font("Helvetica", "B", font_size)
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(col_w[0], 5, " " + headers[0], fill=True)
    pdf.cell(col_w[1], 5, " " + headers[1], fill=True)
    pdf.cell(col_w[2], 5, " " + headers[2], fill=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", "", font_size)
    pdf.set_text_color(*TEXT)
    for a, b, c in rows:
        x0, y0 = pdf.get_x(), pdf.get_y()
        pdf.set_xy(x0, y0)
        pdf.multi_cell(col_w[0], 3.8, " " + a)
        y1 = pdf.get_y()
        pdf.set_xy(x0 + col_w[0], y0)
        pdf.multi_cell(col_w[1], 3.8, " " + b)
        y2 = pdf.get_y()
        pdf.set_xy(x0 + col_w[0] + col_w[1], y0)
        pdf.multi_cell(col_w[2], 3.8, " " + c)
        y3 = pdf.get_y()
        pdf.set_y(max(y1, y2, y3))
    pdf.ln(1)


# ---------------------------------------------------------------------------
# PDF 1 — Microservices redesign (max 4 pages)
# ---------------------------------------------------------------------------

def build_microservices_pdf() -> Path:
    pdf = PDF(orientation="P", unit="mm", format="A4")
    pdf.title_text = "Assignment 1 - Microservices Redesign"
    pdf.set_margins(12, 16, 12)
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.alias_nb_pages()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 8, "Microservices Redesign of OPD-Vertex")
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*GREY)
    pdf.cell(0, 4, "Target scale: 50M users / 1M+ concurrent / ~50k consultations/min  |  p95 < 400 ms reads")
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 4, "Authors: " + AUTHORS)
    pdf.ln(5)

    h1(pdf, "1. System Decomposition - 12 microservices")
    services = [
        ("1. Auth & Identity", "OIDC, JWT, MFA, RBAC, session store."),
        ("2. Patient", "Patient master data, demographics, consent. Read-heavy."),
        ("3. Consultation", "Lifecycle saga orchestrator (recording -> approved)."),
        ("4. Prescription", "Approved, versioned prescriptions (legal record)."),
        ("5. Transcription", "Audio in -> Faster-Whisper on Triton GPU pool."),
        ("6. LLM Orchestrator", "Prompt assembly, vLLM routing, retries, batching."),
        ("7. Suggestive Review", "Independent safety / contradiction model on drafts."),
        ("8. PDF / Document", "Server-side rendering + signing."),
        ("9. Notification", "Email / SMS / push, consumes Kafka."),
        ("10. Audit & Compliance", "Append-only log, GDPR export/erase."),
        ("11. Admin / Prompt Config", "Prompts, templates, feature flags."),
        ("12. Analytics & Reporting", "ClickHouse dashboards fed by Kafka."),
    ]
    two_col_table(pdf, ("Service", "Responsibility"), services, (52, 134), font_size=8.2)

    h2(pdf, "Why split this way")
    bullets(pdf, [
        "DDD bounded contexts: one service per context, one DB per service - no shared schemas.",
        "Independent scaling axes: GPU (Whisper, LLM) vs CPU (CRUD) vs IO (PDF, audit).",
        "Failure isolation: an LLM outage must not block patient lookups or PDF reads.",
        "Compliance: Auth + Audit are isolated and centrally enforced for HIPAA/GDPR.",
        "Team topology: 12 services map cleanly onto 4-6 squads.",
    ])

    pdf.add_page()
    h1(pdf, "2. Architecture Diagram")
    body(pdf,
         "External traffic is REST/JSON terminated at Cloudflare + Kong (JWT validation). "
         "Internal east-west calls are gRPC over an Istio service mesh with mTLS. "
         "Long-running and fan-out work is decoupled via Kafka events and Redis Streams (LLM jobs). "
         "Each service owns its own database; cross-service reads come from event-sourced projections, never shared tables.",
         size=8.7)
    fitted_image(pdf, DIAG / "architecture.png", max_w=pdf.w - 24, max_h=215,
                 caption="Component view - colored bands group bounded contexts; data ownership annotated inside each service.")

    pdf.add_page()
    h1(pdf, "End-to-end consultation flow")
    fitted_image(pdf, DIAG / "sequence.png", max_w=pdf.w - 24, max_h=110,
                 caption="Happy-path sequence: Doctor -> GW -> Consultation saga -> AI pipeline -> Prescription -> PDF -> Kafka.")

    h1(pdf, "3. Benefits and Trade-offs")
    h2(pdf, "Benefits")
    bullets(pdf, [
        "Independent scaling: GPU pools scale separately from CRUD - 60-80% infra savings vs scaling the monolith.",
        "Resilience: Istio bulkheads + circuit breakers keep failures local; LLM outage degrades to draft-later mode.",
        "Faster delivery: 12 deployable units, blue/green per service, no shared release train.",
        "Polyglot persistence: Postgres for legal records, Mongo for drafts, S3 for blobs, ClickHouse for analytics.",
        "Compliance centralized in Auth + Audit, simplifying GDPR/HIPAA audits.",
    ])
    h2(pdf, "Trade-offs")
    bullets(pdf, [
        "Distributed data consistency: sagas (Consultation orchestrates) + outbox pattern; eventual consistency on read models.",
        "Operational complexity: 12 services + mesh + Kafka + GPUs require strong SRE practice and observability.",
        "Network cost / latency: ~2-5 ms per gRPC hop; mitigated by co-locating chatty services in the same node pool.",
        "Local-dev friction: mitigated by Tilt/Skaffold + service stubs and contract tests (Pact).",
        "GPU cost: KEDA scale-to-zero + request batching in vLLM and Triton.",
    ])

    pdf.add_page()
    h1(pdf, "4. Tech Stack and Justification")
    rows = [
        ("Runtime", "Python 3.12 + FastAPI", "Existing codebase; async I/O; OpenAPI native."),
        ("Internal RPC", "gRPC + Protobuf", "Low latency, typed contracts, streaming for audio."),
        ("Edge / Gateway", "Cloudflare + Kong", "Global CDN, WAF, rate limiting, JWT at edge."),
        ("Service mesh", "Istio + Envoy", "mTLS, retries, circuit breakers, traffic shifting."),
        ("Async bus", "Apache Kafka", "Durable, partitioned, replayable; fits audit fan-out."),
        ("Job queue", "Redis Streams", "Sub-ms enqueue for LLM jobs, consumer groups."),
        ("SQL", "PostgreSQL (Patroni + Citus)", "ACID for legal records; mature HA + sharding."),
        ("NoSQL", "MongoDB", "Flexible schema for evolving LLM drafts/transcripts."),
        ("Cache / sessions", "Redis Cluster", "Sub-ms read-through cache, session store."),
        ("Object store", "S3 / MinIO", "Cheap, durable for audio + PDFs; lifecycle to Glacier."),
        ("Search / logs", "Elasticsearch + Loki", "Full-text patient/audit search; log aggregation."),
        ("Analytics", "ClickHouse", "Columnar, sub-second on billions of rows."),
        ("LLM serving", "vLLM (Qwen3 / Llama 3) on H100", "Continuous batching, paged attention."),
        ("Speech-to-text", "Faster-Whisper on Triton", "GPU-batched ASR, streaming."),
        ("Orchestration", "Kubernetes (EKS) + KEDA", "Event-driven autoscaling incl. GPU pools."),
        ("CI/CD", "GitHub Actions + ArgoCD + Trivy", "GitOps, SBOM, image scanning."),
        ("Observability", "Prometheus / Grafana / Tempo / OTel", "RED/USE metrics, distributed traces, SLO alerts."),
        ("Secrets / IaC", "HashiCorp Vault + Terraform + Helm", "Short-lived creds; reproducible multi-region."),
    ]
    three_col_table(pdf, ("Layer", "Choice", "Why"), rows, (32, 56, 94), font_size=7.6)

    h2(pdf, "Deployment topology - multi-region active/active")
    fitted_image(pdf, DIAG / "deployment.png", max_w=pdf.w - 24, max_h=78)

    out = OUT / "Assignment1_Microservices_Redesign.pdf"
    pdf.output(str(out))
    return out


# ---------------------------------------------------------------------------
# PDF 2 — Testing report with real screenshots
# ---------------------------------------------------------------------------

COMPONENT = [
    ("test_security.TestHashPassword", "bcrypt hashing is unique and verifiable."),
    ("test_security.TestVerifyPassword", "Accepts correct, rejects wrong/empty passwords."),
    ("test_security.TestCreateAccessToken", "JWT carries sub/exp; HS256-signed, decodable."),
    ("test_repositories.TestInMemoryPatientRepository", "CRUD + search semantics on patient port."),
    ("test_repositories.TestInMemoryConsultationRepository", "Status transitions and filter-by-patient."),
    ("test_repositories.TestInMemoryPrescriptionRepository", "Versioning of approved prescriptions."),
    ("test_services.TestPatientApplicationService", "Use-case orchestration: list/create/get patient."),
    ("test_services.TestConsultationApplicationService", "Drives the consultation status machine."),
    ("test_document_versioning.TestApplyEdits", "Doctor edits create immutable version snapshots."),
    ("test_document_versioning.TestRestoreVersion", "Restore previous version is non-destructive."),
]

INTEGRATION = [
    ("test_health_dashboard::test_health_endpoint", "GET /health returns 200 + JSON."),
    ("test_auth_flow.TestLoginPage", "Login page renders and POST /login issues a session."),
    ("test_auth_flow.TestConsultationCreate", "Authenticated user creates a consultation via HTTP."),
    ("test_review_api.TestReviewEndpoints", "/review endpoints exercise app + repo + templates."),
    ("test_middleware.TestRequestLoggingMiddleware", "Request-logging middleware emits structured logs."),
]

E2E = [
    ("test_app::test_app_boots", "Whole FastAPI app boots with all routers wired."),
    ("test_app::test_login_page_reachable", "Anonymous user reaches /login (full middleware stack)."),
    ("test_app::test_health_reachable", "/health is reachable via TestClient."),
    ("test_app::test_static_css_mounted", "Static CSS is served end-to-end."),
    ("test_app::test_openapi_schema_available", "/openapi.json is served by the running app."),
]

LOAD = [
    ("test_perf.TestPatientServicePerf", "Latency budget for patient list/create."),
    ("test_perf.TestConsultationServicePerf", "Latency of consultation creation under load."),
    ("test_perf.TestClinicalNoteGenerationPerf", "LLM note-generation latency baseline."),
    ("test_stress.TestPatientRepositoryStress", "1000 concurrent reads/writes against the repo."),
    ("test_stress.TestEndToEndPipelineStress", "Full pipeline: transcribe + LLM + review, 50x."),
]


def build_testing_pdf() -> Path:
    pdf = PDF(orientation="P", unit="mm", format="A4")
    pdf.title_text = "Assignment 2 - Testing Report"
    pdf.set_margins(12, 16, 12)
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.alias_nb_pages()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 8, "Testing Report - OPD-Vertex")
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(*GREY)
    pdf.cell(0, 4, "10 component  +  5 integration  +  5 end-to-end  +  5 load/stress  =  30 tests, all passing.")
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 4, "Authors: " + AUTHORS)
    pdf.ln(5)

    h2(pdf, "Frameworks")
    bullets(pdf, [
        "pytest 8 - test runner (with -v, --tb=line) for all four suites.",
        "pytest-asyncio - async use-case and route tests.",
        "Starlette / FastAPI TestClient (httpx) - integration and E2E HTTP tests.",
        "ThreadPoolExecutor harness - concurrent stress tests under app/tests/stress/.",
        "Time-budget assertions (latency p95/p99) - load tests under app/tests/benchmarks/.",
        "Faster-Whisper + Ollama sidecars - real-LLM E2E (excluded from CI by default).",
    ])

    h2(pdf, "How to run")
    pdf.set_font("Courier", "", 8)
    pdf.set_fill_color(245, 245, 248)
    pdf.set_text_color(*TEXT)
    pdf.multi_cell(0, 4, " pytest app/tests/unit          # 10 component tests (146 cases)\n"
                          " pytest app/tests/integration   # 5 integration test suites (20 cases)\n"
                          " pytest app/tests/smoke         # 5 end-to-end smoke tests\n"
                          " pytest app/tests/stress        # 5 stress test suites (14 cases)\n"
                          " pytest app/tests/benchmarks    # 5 load / latency-budget tests (10 cases)",
                   fill=True)
    pdf.ln(2)

    h1(pdf, "Component tests (10) - app/tests/unit/")
    two_col_table(pdf, ("Test", "What it verifies"), COMPONENT, (74, 112), font_size=7.8)
    fitted_image(pdf, SHOTS / "01_component.png", max_w=pdf.w - 24, max_h=70,
                 caption="pytest -v app/tests/unit  ->  146 passed in 8.74s")

    pdf.add_page()
    h1(pdf, "Integration tests (5) - app/tests/integration/")
    two_col_table(pdf, ("Test", "What it verifies"), INTEGRATION, (74, 112), font_size=7.8)
    fitted_image(pdf, SHOTS / "02_integration.png", max_w=pdf.w - 24, max_h=80,
                 caption="pytest -v app/tests/integration  ->  20 passed in 1.32s")

    h1(pdf, "End-to-end tests (5) - app/tests/smoke/")
    two_col_table(pdf, ("Test", "What it verifies"), E2E, (74, 112), font_size=7.8)
    fitted_image(pdf, SHOTS / "03_e2e.png", max_w=pdf.w - 24, max_h=55,
                 caption="pytest -v app/tests/smoke  ->  6 passed in 0.86s")

    pdf.add_page()
    h1(pdf, "Load and stress tests (5) - app/tests/{benchmarks,stress}/")
    two_col_table(pdf, ("Test", "What it verifies"), LOAD, (74, 112), font_size=7.8)
    fitted_image(pdf, SHOTS / "05_benchmarks.png", max_w=pdf.w - 24, max_h=60,
                 caption="Latency budgets: 10 passed in 0.78s")
    fitted_image(pdf, SHOTS / "04_stress.png", max_w=pdf.w - 24, max_h=80,
                 caption="Concurrency / saturation: 14 passed in 0.93s")

    h2(pdf, "Critical resource targeted")
    body(pdf,
         "The clinical pipeline (Whisper transcription -> Qwen3 normalization -> note generation -> "
         "suggestive review) is the bottleneck because it is GPU-bound and synchronous from the doctor's "
         "perspective. Latency budgets (benchmarks/) protect the per-request SLA, while the stress suite "
         "(stress/) saturates the full pipeline and the underlying repositories with concurrent producers "
         "to surface contention before production rollout.",
         size=8.5)

    out = OUT / "Assignment2_Testing_Report.pdf"
    pdf.output(str(out))
    return out


if __name__ == "__main__":
    a = build_microservices_pdf()
    b = build_testing_pdf()
    print("Wrote:", a)
    print("Wrote:", b)
