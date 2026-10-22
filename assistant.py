from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Note, Task
from ..services.ai_service import answer, extract_actions
from ..utils import audit, owned_or_404, parse_datetime, require_verified, safe_text

bp = Blueprint("assistant", __name__)


@bp.get("/assistant")
@login_required
@require_verified
def chat():
    return render_template("assistant/chat.html")


@bp.post("/api/assistant/ask")
@login_required
@require_verified
def ask():
    data = request.get_json(silent=True) or {}
    question = safe_text(data.get("question"), 500)
    if not question:
        return jsonify(error="Ask a question about your saved memories."), 400
    notes = Note.query.filter_by(user_id=current_user.id, is_archived=False).order_by(Note.updated_at.desc()).limit(30).all()
    result = answer(question, notes)
    audit("assistant_question", user=current_user, source_count=result["source_count"])
    return jsonify(**result)


@bp.post("/api/assistant/confirm-actions/<int:note_id>")
@login_required
@require_verified
def confirm_actions(note_id):
    note = owned_or_404(Note, note_id)
    payload = request.get_json(silent=True) or {}
    actions = payload.get("actions")
    if not isinstance(actions, list) or not actions:
        actions = extract_actions(note.content)["actions"]
    created = []
    for item in actions[:8]:
        if not isinstance(item, dict) or not safe_text(item.get("title"), 200):
            continue
        task = Task(user_id=current_user.id, source_note_id=note.id, title=safe_text(item.get("title"), 200), description=safe_text(item.get("description"), 1000), due_at=parse_datetime(item.get("due_date")), priority=item.get("priority") if item.get("priority") in {"low", "medium", "high"} else "medium")
        db.session.add(task)
        created.append(task)
    db.session.commit()
    audit("ai_actions_confirmed", user=current_user, note_id=note.id, count=len(created))
    return jsonify(created=[{"id": task.id, "title": task.title} for task in created])
