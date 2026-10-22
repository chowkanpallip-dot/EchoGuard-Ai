from datetime import datetime, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from flask_login import UserMixin

from .extensions import db, login_manager


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


note_tags = db.Table(
    "note_tags",
    db.Column("note_id", db.Integer, db.ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(512), nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False, index=True)
    failed_login_count = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    notes = db.relationship("Note", back_populates="user", cascade="all, delete-orphan")
    tasks = db.relationship("Task", back_populates="user", cascade="all, delete-orphan")
    tags = db.relationship("Tag", back_populates="user", cascade="all, delete-orphan")
    audit_events = db.relationship("AuditEvent", back_populates="user", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = PasswordHasher().hash(password)

    def check_password(self, password):
        try:
            return PasswordHasher().verify(self.password_hash, password)
        except (VerifyMismatchError, TypeError, ValueError):
            return False

    @property
    def is_locked(self):
        return bool(self.locked_until and self.locked_until > utcnow())


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id)) if user_id else None


class Note(db.Model):
    __tablename__ = "notes"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text, nullable=True)
    key_points = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(80), default="Personal", nullable=False, index=True)
    is_favorite = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_archived = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    user = db.relationship("User", back_populates="notes")
    tags = db.relationship("Tag", secondary=note_tags, back_populates="notes")
    tasks = db.relationship("Task", back_populates="source_note")


class Tag(db.Model):
    __tablename__ = "tags"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(50), nullable=False)
    user = db.relationship("User", back_populates="tags")
    notes = db.relationship("Note", secondary=note_tags, back_populates="tags")
    __table_args__ = (db.UniqueConstraint("user_id", "name", name="uq_tag_user_name"),)


class Task(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source_note_id = db.Column(db.Integer, db.ForeignKey("notes.id", ondelete="SET NULL"), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    due_at = db.Column(db.DateTime, nullable=True, index=True)
    reminder_at = db.Column(db.DateTime, nullable=True)
    priority = db.Column(db.String(20), default="medium", nullable=False, index=True)
    status = db.Column(db.String(20), default="open", nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    user = db.relationship("User", back_populates="tasks")
    source_note = db.relationship("Note", back_populates="tasks")


class EmailToken(db.Model):
    __tablename__ = "email_tokens"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = db.Column(db.String(128), unique=True, nullable=False, index=True)
    kind = db.Column(db.String(30), nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    user = db.relationship("User")


class AuditEvent(db.Model):
    __tablename__ = "audit_events"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    event_type = db.Column(db.String(80), nullable=False, index=True)
    ip_address = db.Column(db.String(64), nullable=True)
    metadata_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)
    user = db.relationship("User", back_populates="audit_events")
