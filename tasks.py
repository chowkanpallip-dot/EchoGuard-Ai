from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Task, utcnow
from ..utils import audit, owned_or_404, parse_datetime, require_verified, safe_text

bp = Blueprint("tasks", __name__)


@bp.get("/tasks")
@login_required
@require_verified
def index():
    tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.status.asc(), Task.due_at.asc().nullslast(), Task.created_at.desc()).all()
    return render_template("tasks/index.html", tasks=tasks)


@bp.post("/api/tasks")
@login_required
@require_verified
def create_task():
    data = request.get_json(silent=True) or request.form
    title = safe_text(data.get("title"), 200)
    if not title:
        return jsonify(error="A task title is required."), 400
    priority = safe_text(data.get("priority"), 20).lower() or "medium"
    if priority not in {"low", "medium", "high"}:
        priority = "medium"
    task = Task(user_id=current_user.id, title=title, description=safe_text(data.get("description"), 1000), due_at=parse_datetime(data.get("due_at")), reminder_at=parse_datetime(data.get("reminder_at")), priority=priority)
    db.session.add(task)
    db.session.commit()
    audit("task_created", user=current_user, task_id=task.id)
    return jsonify(task=_serialize(task)), 201


@bp.patch("/api/tasks/<int:task_id>")
@login_required
@require_verified
def update_task(task_id):
    task = owned_or_404(Task, task_id)
    data = request.get_json(silent=True) or {}
    if "title" in data:
        task.title = safe_text(data.get("title"), 200) or task.title
    if "description" in data:
        task.description = safe_text(data.get("description"), 1000)
    if "priority" in data and data["priority"] in {"low", "medium", "high"}:
        task.priority = data["priority"]
    if "due_at" in data:
        task.due_at = parse_datetime(data.get("due_at"))
    if "reminder_at" in data:
        task.reminder_at = parse_datetime(data.get("reminder_at"))
    if "status" in data and data["status"] in {"open", "completed"}:
        task.status = data["status"]
        task.completed_at = utcnow() if task.status == "completed" else None
    db.session.commit()
    return jsonify(task=_serialize(task))


@bp.post("/api/tasks/<int:task_id>/toggle")
@login_required
@require_verified
def toggle_task(task_id):
    task = owned_or_404(Task, task_id)
    task.status = "completed" if task.status == "open" else "open"
    task.completed_at = utcnow() if task.status == "completed" else None
    db.session.commit()
    audit("task_toggled", user=current_user, task_id=task.id, status=task.status)
    return jsonify(task=_serialize(task))


@bp.delete("/api/tasks/<int:task_id>")
@login_required
@require_verified
def delete_task(task_id):
    task = owned_or_404(Task, task_id)
    db.session.delete(task)
    db.session.commit()
    audit("task_deleted", user=current_user, task_id=task_id)
    return jsonify(deleted=True)


def _serialize(task):
    return {"id": task.id, "title": task.title, "description": task.description or "", "due_at": task.due_at.isoformat() if task.due_at else None, "reminder_at": task.reminder_at.isoformat() if task.reminder_at else None, "priority": task.priority, "status": task.status}
