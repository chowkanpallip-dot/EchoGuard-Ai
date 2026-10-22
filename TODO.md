# EchoGuard AI delivery checklist

- [x] A new user can register with validated email/password, receives an expiring single-use verification link in configured email delivery or an explicitly labeled development outbox, and cannot use private features before verification.
- [x] Users can log in, log out through a CSRF-protected POST, recover access with a single-use expiring password-reset link, and are protected by secure cookies, CSRF, rate limiting, lockouts, and safe error handling.
- [x] Every private page and JSON endpoint requires authentication and every note, task, tag, token, and audit event is scoped to its owning user.
- [x] Users can save text memories, capture browser speech transcripts with manual fallback, tag/category/favorite/archive memories, and search their own library.
- [x] Users can request concise summaries, key points, and extracted action suggestions; AI receives only authorized notes, treats content as untrusted, reports truthful provider/local provenance, and never persists consequential actions without confirmation.
- [x] Users can ask natural-language questions about their own memories and receive “unavailable” when the answer is not supported by saved context.
- [x] Users can create, edit, complete, delete, prioritize, due-date, and reminder tasks from the task manager and confirmed AI suggestions.
- [x] The responsive interface includes landing, auth, dashboard, capture, library, assistant, tasks, settings, dark mode, validation, loading, empty, and helpful error states.
- [x] The repository includes modular Flask source, requirements, environment example, a committed Flask-Migrate revision, database instructions, sample data, README, route manifest, and automated tests for registration, verification, login, reset, CSRF, authorization, isolation, APIs, and core flows.
- [x] Local SQLite and production DATABASE_URL operation are documented; external AI/email integrations are opt-in and never represented as configured when they are not.

## Validation evidence

`pytest -q` passes 10 tests. Fresh SQLite migration upgrade creates `users`, `notes`, `tasks`, `tags`, `note_tags`, `email_tokens`, and `audit_events`; a pre-existing complete schema, including the empty `alembic_version` state left by an interrupted migration, is stamped idempotently before upgrade. Live Preview returns `{"status":"ok"}` from `/health`, serves the 13-route manifest at `/manus-routes.json`, renders public/auth pages, and rejects a state-changing login POST without a CSRF token with HTTP 400.
