import json

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import or_

from ..extensions import db
from ..forms import NoteForm
from ..models import Note, Tag
from ..services.ai_service import extract_actions, summarize
from ..utils import audit, owned_or_404, require_verified, safe_text

bp = Blueprint("memories", __name__)


@bp.get("/memories")
@login_required
@require_verified
def library():
    query = safe_text(request.args.get("q"), 200)
    category = safe_text(request.args.get("category"), 80)
    notes_query = Note.query.filter_by(user_id=current_user.id)
    if query:
        like = f"%{query}%"
        notes_query = notes_query.filter(or_(Note.title.ilike(like), Note.content.ilike(like), Note.summary.ilike(like)))
    if category:
        notes_query = notes_query.filter_by(category=category)
    notes = notes_query.order_by(Note.is_archived.asc(), Note.updated_at.desc()).all()
    categories = [row[0] for row in db.session.query(Note.category).filter_by(user_id=current_user.id).distinct().order_by(Note.category).all()]
    return render_template("memories/library.html", notes=notes, categories=categories, query=query, selected_category=category)


@bp.route("/memories/new", methods=["GET", "POST"])
@login_required
@require_verified
def create():
    form = NoteForm()
    if form.validate_on_submit():
        note = Note(user_id=current_user.id, title=form.title.data.strip(), content=form.content.data.strip(), category=form.category.data.strip() or "Personal")
        _apply_tags(note, form.tags.data)
        db.session.add(note)
        db.session.commit()
        audit("memory_created", user=current_user, note_id=note.id)
        flash("Memory saved. You can ask EchoGuard to summarize it or extract actions.", "success")
        return redirect(url_for("memories.library"))
    return render_template("memories/capture.html", form=form)


@bp.get("/memories/<int:note_id>")
@login_required
@require_verified
def detail(note_id):
    note = owned_or_404(Note, note_id)
    return render_template("memories/detail.html", note=note)


@bp.post("/api/memories/<int:note_id>/summarize")
@login_required
@require_verified
def summarize_memory(note_id):
    note = owned_or_404(Note, note_id)
    result = summarize(note.content)
    note.summary = result["summary"]
    note.key_points = json.dumps(result["key_points"])
    db.session.commit()
    audit("memory_summarized", user=current_user, note_id=note.id)
    return jsonify(summary=note.summary, key_points=result["key_points"], source=result.get("source", "local"))


@bp.post("/api/memories/<int:note_id>/extract-actions")
@login_required
@require_verified
def actions_memory(note_id):
    note = owned_or_404(Note, note_id)
    result = extract_actions(note.content)
    return jsonify(actions=result["actions"], source=result["source"], requires_confirmation=True)


@bp.post("/api/memories/<int:note_id>/favorite")
@login_required
@require_verified
def favorite(note_id):
    note = owned_or_404(Note, note_id)
    note.is_favorite = not note.is_favorite
    db.session.commit()
    return jsonify(is_favorite=note.is_favorite)


@bp.post("/api/memories/<int:note_id>/archive")
@login_required
@require_verified
def archive(note_id):
    note = owned_or_404(Note, note_id)
    note.is_archived = not note.is_archived
    db.session.commit()
    return jsonify(is_archived=note.is_archived)


def _apply_tags(note, raw_tags):
    for raw in (raw_tags or "").split(","):
        name = " ".join(raw.strip().split())[:50]
        if not name:
            continue
        tag = Tag.query.filter_by(user_id=current_user.id, name=name).first()
        if not tag:
            tag = Tag(user_id=current_user.id, name=name)
            db.session.add(tag)
        note.tags.append(tag)

