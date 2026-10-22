import json

from echoguard.extensions import db
from echoguard.models import Note, Task, User

from .conftest import login


def test_private_pages_require_login(client):
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert "/auth/login" in response.location
    assert client.get("/api/tasks").status_code in {302, 405}


def test_csrf_rejects_state_change_without_token(app, client, verified_user):
    app.config["WTF_CSRF_ENABLED"] = True
    response = client.post("/auth/login", data={"email": "owner@example.com", "password": "StrongPassword123!"})
    assert response.status_code == 400


def test_memory_and_task_apis_are_user_scoped(app, client, verified_user):
    login(client)
    response = client.post("/api/tasks", json={"title": "Review the outline", "priority": "high"}, headers={"X-CSRFToken": ""})
    # TestConfig disables CSRF; this also proves the API path is functional.
    assert response.status_code == 201
    task_id = response.get_json()["task"]["id"]
    with app.app_context():
        owner = db.session.get(User, verified_user)
        note = Note(user_id=verified_user, title="Private plan", content="Send the outline tomorrow", category="Work")
        db.session.add(note)
        db.session.commit()
        note_id = note.id
        other = User(email="other@example.com", name="Other", is_verified=True)
        other.set_password("StrongPassword123!")
        db.session.add(other)
        db.session.commit()
        other_id = other.id
    client.post("/auth/logout")
    login(client, email="other@example.com")
    assert client.get(f"/memories/{note_id}").status_code == 404
    assert client.patch(f"/api/tasks/{task_id}", json={"title": "Hijack"}).status_code == 404


def test_memory_search_and_summary(app, client, verified_user):
    with app.app_context():
        note = Note(user_id=verified_user, title="Monday plan", content="Call Maya after lunch. Send the latest draft.", category="Work")
        db.session.add(note)
        db.session.commit()
        note_id = note.id
    login(client)
    response = client.get("/memories?q=Maya")
    assert b"Monday plan" in response.data
    response = client.post(f"/api/memories/{note_id}/summarize", headers={"X-CSRFToken": ""})
    assert response.status_code == 200
    assert response.get_json()["summary"]
    response = client.post(f"/api/memories/{note_id}/extract-actions", headers={"X-CSRFToken": ""})
    assert response.status_code == 200
    assert response.get_json()["requires_confirmation"] is True


def test_confirmed_actions_create_owned_tasks(app, client, verified_user):
    with app.app_context():
        note = Note(user_id=verified_user, title="Action note", content="Call the team", category="Work")
        db.session.add(note)
        db.session.commit()
        note_id = note.id
    login(client)
    response = client.post(f"/api/assistant/confirm-actions/{note_id}", json={"actions":[{"title":"Call the team","priority":"high","due_date":"2026-11-01"}]})
    assert response.status_code == 200
    with app.app_context():
        task = Task.query.filter_by(user_id=verified_user, title="Call the team").one()
        assert task.due_at.strftime("%Y-%m-%d") == "2026-11-01"
