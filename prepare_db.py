"""Prepare a database for migrations without recreating an existing schema.

A development Preview may have created the initial schema with SQLAlchemy before
Flask-Migrate was enabled. When that complete schema exists without Alembic's
version table, mark it at the committed initial revision and let `db upgrade`
handle all future revisions normally.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect, text

from echoguard import create_app
from echoguard.config import Config
from echoguard.extensions import db
from flask_migrate import stamp


def main():
    app = create_app(Config)
    with app.app_context():
        tables = set(inspect(db.engine).get_table_names())
        expected_tables = {"users", "notes", "tasks", "tags", "note_tags", "email_tokens", "audit_events"}
        has_revision = False
        if "alembic_version" in tables:
            has_revision = bool(db.session.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).first())
        if expected_tables <= tables and not has_revision:
            app.logger.warning("Existing EchoGuard schema detected without Alembic version; stamping current head.")
            stamp(revision="head")


if __name__ == "__main__":
    main()
