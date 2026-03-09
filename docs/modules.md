# Module Guide

- `auth`: placeholder identity workflow and future authorization hooks.
- `patients`: patient CRUD scaffolding backed by in-memory data.
- `consultations`: consultation creation and status lifecycle shell.
- `transcription`: mock speech-to-text service and transcript repository contract.
- `clinical_notes`: generated SOAP note and prescription draft contract.
- `suggestive_mode`: independent clinical safety review placeholder.
- `review`: doctor-facing review orchestration between transcript, notes, and suggestions.
- `prescriptions`: finalized prescription records and versioning-ready repository.
- `pdf`: placeholder output contract for ReportLab-backed generation.
- `email`: template repository and outbound email abstraction.
- `audit`: audit log contract and recent activity feed placeholder.
- `admin`: prompt/email configuration overview page.
