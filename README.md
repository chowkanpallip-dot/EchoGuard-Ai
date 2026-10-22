# Database migrations

This repository uses Flask-Migrate. For a fresh local SQLite database, run `flask --app run.py db init` once, then `flask --app run.py db migrate -m "initial schema"` and `flask --app run.py db upgrade`. The included app factory also creates tables for a zero-friction local demo.

For a shared or production database, always run `flask --app run.py db upgrade` as a release step before starting Gunicorn. The managed Webdev database is MySQL-compatible; use its injected `DATABASE_URL`. Local development defaults to SQLite.
