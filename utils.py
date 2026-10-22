import hashlib
import json
import secrets
from datetime import timedelta
from functools import wraps

from flask import abort, current_app, flash, redirect, request, url_for
from flask_login import current_user
from sqlalchemy import update

from .extensions import db
from .models import AuditEvent, EmailToken, utcnow


def normalize_email(email):
    return (email or "").strip().lower()


def make_token(user, kind, hours=24):
    raw = secrets.token_urlsafe(32)
    record = EmailToken(
        user_id=user.id,
        token_hash=hashlib.sha256(raw.encode()).hexdigest(),
        kind=kind,
        expires_at=utcnow() + timedelta(hours=hours),
    )
    db.session.add(record)
    db.session.commit()
    return raw


def consume_token(raw, kind):
    if not raw:
        return None
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    now = utcnow()
    result = db.session.execute(
        update(EmailToken)
        .where(
            EmailToken.token_hash == token_hash,
            EmailToken.kind == kind,
            EmailToken.used_at.is_(None),
            EmailToken.expires_at > now,
        )
        .values(used_at=now)
    )
    if result.rowcount != 1:
        db.session.rollback()
        return None
    record = EmailToken.query.filter_by(token_hash=token_hash, kind=kind).first()
    db.session.commit()
    return record.user if record else None


def audit(event_type, user=None, **metadata):
    event = AuditEvent(
        user_id=getattr(user or current_user, "id", None),
        event_type=event_type,
        ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
        metadata_json=json.dumps(metadata, default=str)[:2000] if metadata else None,
    )
    db.session.add(event)
    db.session.commit()


def owned_or_404(model, object_id):
    obj = model.query.filter_by(id=object_id, user_id=current_user.id).first()
    if not obj:
        abort(404)
    return obj


def safe_text(value, max_length=10000):
    return (value or "").strip()[:max_length]


def parse_datetime(value):
    if not value:
        return None
    from datetime import datetime
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def flash_form_error(message):
    flash(message, "danger")


def require_verified(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_verified:
            flash("Verify your email before using private memory features.", "warning")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped
