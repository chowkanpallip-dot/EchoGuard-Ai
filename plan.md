# EchoGuard AI implementation plan

## Approach

EchoGuard AI is implemented as a conventional Flask application that serves server-rendered HTML and progressive-enhancement JavaScript. The app factory in `echoguard/app.py` owns configuration and extensions; blueprints separate public pages, authentication, memories, tasks, and the AI assistant. SQLAlchemy models use an environment-provided `DATABASE_URL` when available and SQLite by default for local development, keeping the schema portable to PostgreSQL/MySQL-compatible deployments. Flask-Migrate owns additive schema migrations.

Authentication uses Flask-Login with Argon2id password hashing, signed expiring single-use verification/reset tokens, CSRF protection, secure session configuration, login throttling, lockouts, and strict owner filters on every private query. Development email delivery is explicit and safe: messages are logged to the terminal and the latest link is surfaced only in development UI; production requires SMTP settings and never falls back silently.

AI behavior is isolated in `echoguard/services/ai_service.py`. If `LLM_API_URL` and `LLM_API_KEY` are configured, it calls an OpenAI-compatible provider with bounded, user-scoped context. Otherwise it uses a deterministic local summarizer/action extractor so the core workflow remains runnable offline. Prompts explicitly treat memory text as untrusted data, and the assistant only receives notes owned by the authenticated user. Suggested actions are previewed and require confirmation before persistence.

The UI uses Bootstrap 5 from CDN plus project CSS and small vanilla JavaScript modules. It has a white/electric-blue visual system, dark mode via `localStorage`, responsive navigation, accessible feedback, loading states, empty states, browser SpeechRecognition when supported, and manual text fallback. `manus-routes.json` declares all page routes before the development server starts.

## Design

Three possible directions: **Quiet command center** (0.07), **Editorial memory atlas** (0.06), **Soft glass productivity lab** (0.05). Chosen: **Quiet command center**.

- **Design Movement:** Modern Swiss-influenced productivity UI with calm information hierarchy and precise utility panels.
- **Core Principles:** clarity before decoration; visible provenance; low-friction capture; confident but non-alarming security cues.
- **Color Philosophy:** near-white surfaces create mental room, ink navy anchors attention, and electric blue marks moments of action and trust. Teal is reserved for healthy completion, amber for pending review, and coral for destructive states.
- **Layout Paradigm:** a left rail and asymmetric dashboard bands rather than a centered marketing grid; dense data lives in editorial rows, not oversized cards.
- **Signature Elements:** a blue “signal line” motif, compact provenance labels (“Saved memory”, “AI suggestion”), and softly rounded capsule controls.
- **Interaction Philosophy:** every AI result is inspectable and confirmable; destructive actions are explicit; capture is always one click away.
- **Animation:** 160–220ms ease-out fades and short vertical lifts for panels, with reduced-motion support and no attention-grabbing loops.
- **Typography System:** Inter for UI and headings, system monospace for timestamps and provenance labels; strong 700 headings, readable 400 body copy, generous line height.
- **Brand Essence:** A private, practical memory layer for people who think in motion; calm, grounded, precise.
- **Brand Voice:** direct and reassuring. Example lines: “Keep the thought. Find it when it matters.” and “AI can suggest the next step; you stay in control.”
- **Wordmark & Logo:** an abstract echo waveform inside a shield outline, paired with a compact wordmark.
- **Signature Brand Color:** Echo Blue `#2864F0`.

## Project structure

- `echoguard/`: application package, configuration, extensions, models, services, forms, and blueprints.
- `echoguard/templates/`: server-rendered pages and reusable UI partials.
- `echoguard/static/`: CSS and progressive-enhancement JavaScript.
- `migrations/`: Flask-Migrate metadata and migration instructions.
- `tests/`: pytest fixtures and security/core behavior coverage.
- `scripts/`: local database initialization and sample-data seeding.
- `run.py`: local entry point; `wsgi.py`: production entry point.

## Build workflow

1. Install Python dependencies from `requirements.txt`.
2. Copy `.env.example` to `.env` and choose SQLite or provide `DATABASE_URL`.
3. Run `flask --app run.py db upgrade` and `python scripts/seed_demo.py`.
4. Start with `python run.py` and use the local verification link shown after registration.
5. Run `pytest -q` for the automated suite.
6. For production, set a strong `SECRET_KEY`, SMTP values, `DATABASE_URL`, and optional LLM provider variables; run migrations before starting Gunicorn.
