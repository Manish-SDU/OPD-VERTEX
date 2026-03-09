# TODO — Database Integration

All domain models, ORM tables, connection helpers, and repository stubs are already created.
The app currently boots with **in-memory mocks**. Your job is to implement the real DB repositories.

---

## Mats — SQL (MySQL)

### What's already done
- **ORM models**: `app/infrastructure/db/sql/models/tables.py` — all 5 tables (staff, patients, consultations, prescriptions, audit_logs) with correct columns, FKs, and constraints
- **Connection helper**: `app/infrastructure/db/sql/connection.py` — `get_engine()` and `get_session()`
- **Alembic config**: `alembic.ini` + `alembic/env.py` — reads DB URL from app settings
- **Domain models** (the Pydantic classes your repos return): `app/domain/auth/models.py`, `app/domain/patients/models.py`, `app/domain/consultations/models.py`, `app/domain/prescriptions/models.py`, `app/domain/audit/models.py`

### What you need to do

1. **Install deps**: `pip install -e .[dev]` (sqlalchemy, pymysql, alembic are already in pyproject.toml)

2. **Generate the first migration**:
   ```bash
   alembic revision --autogenerate -m "create_all_tables"
   alembic upgrade head
   ```

3. **Implement 5 repository classes** in `app/infrastructure/db/sql/repositories/sql_repos.py`:
   - `SqlStaffRepository(StaffRepository)` — implement `get_by_email()`, `get_by_id()`
   - `SqlPatientRepository(PatientRepository)` — implement `list_all()`, `get_by_id()`, `create()`
   - `SqlConsultationRepository(ConsultationRepository)` — implement `list_all()`, `get_by_id()`, `create()`, `update_status()`
   - `SqlPrescriptionRepository(PrescriptionRepository)` — implement `list_all()`, `get_by_id()`, `create()`
   - `SqlAuditLogRepository(AuditLogRepository)` — implement `list_recent()`, `append()`

   Each method: query ORM row from `tables.py` → convert to domain Pydantic model → return it. See the example pattern in that file.

4. **Wire them in** `app/api/deps.py`: replace `InMemory*` with your `Sql*` classes, passing `get_session()`.

---

## Gabriele — NoSQL (MongoDB)

### What's already done
- **Connection helper**: `app/infrastructure/db/mongo/connection.py` — `get_database()` returns a pymongo Database
- **Collection names**: `app/infrastructure/db/mongo/collections/names.py` — 4 constants: `EMAIL_TEMPLATES`, `LLM_PROMPTS`, `GENERATED_DOCUMENTS`, `CONSULTATION_DOCUMENTS`
- **Seed script**: `app/infrastructure/db/mongo/seeds.py` — inserts initial llm_prompts + email_templates
- **Domain models** (the Pydantic classes your repos return): `app/domain/clinical_notes/models.py` (GeneratedDocument, ConsultationDocument, LlmPromptConfig), `app/domain/email/models.py` (EmailTemplate)

### What you need to do

1. **Install deps**: `pip install -e .[dev]` (pymongo is already in pyproject.toml)

2. **Run the seed script** (once MongoDB is running):
   ```bash
   python -m app.infrastructure.db.mongo.seeds
   ```

3. **Implement 4 repository classes** in `app/infrastructure/db/mongo/repositories/mongo_repos.py`:
   - `MongoEmailTemplateRepository(EmailTemplateRepository)` — implement `list_templates()`, `get_by_id()`
   - `MongoPromptRepository(PromptRepository)` — implement `list_prompts()`, `get_by_id()`
   - `MongoGeneratedDocumentRepository(GeneratedDocumentRepository)` — implement `get_by_consultation_id()`, `save()`
   - `MongoConsultationDocumentRepository(ConsultationDocumentRepository)` — implement `get_by_consultation_id()`, `save()`

   Each method: query pymongo collection → convert dict to domain Pydantic model → return it. See the example pattern in that file.

4. **Wire them in** `app/api/deps.py`: replace `InMemory*` with your `Mongo*` classes, passing `get_database()`.

---

## After both are done

- Set `USE_MOCK_ADAPTERS=false` in `.env`
- Run `docker compose up` to verify everything works end-to-end
- Introduce basic RBAC for `doctor` and `admin` roles.
- Protect sensitive routes with auth dependencies.
- Add real logout behavior and minimal access audit logging.

### Where to implement it

- Contracts already defined in `app/domain/auth/models.py`
- Application service: `app/application/auth/services.py`
- Current mock adapter to replace: `app/infrastructure/auth/mock.py`
- Security/config helpers: `app/core/security.py` and `app/core/config.py`
- Route hooks / dependencies: `app/api/deps.py` and `app/api/routes/auth.py`
