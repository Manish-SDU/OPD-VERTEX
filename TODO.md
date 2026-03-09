# TODO

## Database

### What to do

- Implement real MySQL repositories for `staff`, `patients`, `consultations`, `prescriptions`, and `audit_logs`.
- Implement real Mongo repositories for `email_templates`, `llm_prompts`, `generated_documents`, and `consultation_documents`.
- Add ORM models / mapping and document models.
- Add SQL migrations and initial seeds.
- Connect the real repositories to the dependency wiring.
- Keep the mocks only as optional dev/test fallbacks if useful.

### Where to implement it

- Contracts already defined in `app/domain/*/models.py`
- Current wiring in `app/api/deps.py`
- MySQL: `app/infrastructure/db/sql/models/` and `app/infrastructure/db/sql/repositories/`
- SQL migrations/seeds: `app/infrastructure/db/sql/migrations/` and `app/infrastructure/db/sql/seeds/`
- Mongo: `app/infrastructure/db/mongo/collections/` and `app/infrastructure/db/mongo/repositories/`
- Mongo seeds: `app/infrastructure/db/mongo/seeds/`
- Current mocks to replace: `app/infrastructure/persistence/in_memory/repositories.py`

## Authentication

### What to do

- Implement real login with password verification.
- Add session or token management.
- Resolve the current user dynamically instead of returning a fixed mock user.
- Introduce basic RBAC for `doctor` and `admin` roles.
- Protect sensitive routes with auth dependencies.
- Add real logout behavior and minimal access audit logging.

### Where to implement it

- Contracts already defined in `app/domain/auth/models.py`
- Application service: `app/application/auth/services.py`
- Current mock adapter to replace: `app/infrastructure/auth/mock.py`
- Security/config helpers: `app/core/security.py` and `app/core/config.py`
- Route hooks / dependencies: `app/api/deps.py` and `app/api/routes/auth.py`
