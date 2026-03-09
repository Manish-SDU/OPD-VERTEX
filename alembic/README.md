# Alembic Migrations

Generate and apply SQL schema migrations.

```bash
# Generate a new migration from ORM model changes
alembic revision --autogenerate -m "description"

# Apply all pending migrations
alembic upgrade head
```

ORM models: `app/infrastructure/db/sql/models/tables.py`
