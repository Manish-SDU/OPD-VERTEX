# Contributing

## Conventions

- Keep dependencies pointed inward toward `app/domain`.
- Add real implementations behind existing interfaces instead of coupling routes to infrastructure.
- Prefer small modules and explicit DTOs over implicit dict-based payloads.
- Leave TODO comments only where ownership is still intentionally deferred.

## Branch Naming

- `feature/<area>-<short-description>`
- `fix/<area>-<short-description>`
- `docs/<area>-<short-description>`

## Where Future Work Belongs

- SQL persistence: `app/infrastructure/db/sql`
- Mongo persistence: `app/infrastructure/db/mongo`
- AI adapters: `app/infrastructure/ai`
- PDF work: `app/infrastructure/pdf`
- Email delivery: `app/infrastructure/email`
- Auth hardening: `app/infrastructure/auth` and `app/application/auth`
