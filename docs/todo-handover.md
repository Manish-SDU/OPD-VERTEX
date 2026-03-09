# Handover TODO

- DB work goes into `app/infrastructure/db/sql` and `app/infrastructure/db/mongo`, with contracts already defined in `app/domain`.
- AI transcription work goes into `app/infrastructure/ai/transcription`; use `TranscriptionService`.
- AI note generation and suggestive mode work go into `app/infrastructure/ai/llm`; keep generators separate.
- PDF generation work goes into `app/infrastructure/pdf`; implement `PdfGenerator`.
- Auth/session work goes into `app/infrastructure/auth`; keep RBAC checks outside route bodies.
- Email delivery work goes into `app/infrastructure/email`; implement `EmailService` and migrate template storage to Mongo.
- Review approval persistence should project finalized prescriptions into SQL after clinician approval.
