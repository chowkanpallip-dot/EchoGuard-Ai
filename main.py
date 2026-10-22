from flask import Blueprint, jsonify, render_template
from flask_login import current_user, login_required

from ..models import Note, Task, utcnow
from ..utils import require_verified

bp = Blueprint("main", __name__)


@bp.get("/dashboard")
@login_required
@require_verified
def dashboard():
    recent_notes = Note.query.filter_by(user_id=current_user.id, is_archived=False).order_by(Note.updated_at.desc()).limit(5).all()
    upcoming_tasks = Task.query.filter_by(user_id=current_user.id, status="open").order_by(Task.due_at.asc().nullslast(), Task.created_at.desc()).limit(5).all()
    return render_template("main/dashboard.html", recent_notes=recent_notes, upcoming_tasks=upcoming_tasks, now=utcnow())


@bp.get("/health")
def health():
    return jsonify(status="ok", service="echoguard-ai")
