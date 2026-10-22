import hashlib
import re
from datetime import timedelta

from echoguard.extensions import db
from echoguard.models import EmailToken, User, utcnow
from echoguard.utils import make_token


def test_registration_creates_hashed_unverified_user_and_dev_link(client, app):
    response = client.post("/auth/register", data={"name": "Ada", "email": "ada@example.com", "password": "StrongPassword123!", "confirm_password": "StrongPassword123!"}, follow_redirects=True)
    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(email="ada@example.com").one()
        assert user.is_verified is False
        assert user.password_hash != "StrongPassword123!"
        assert user.check_password("StrongPassword123!")
        token = EmailToken.query.filter_by(user_id=user.id, kind="verify").one()
        assert token.used_at is None


def test_email_verification_is_single_use(client, app):
    with app.app_context():
        user = User(email="verify@example.com", name="Verify", password_hash="x")
        user.set_password("StrongPassword123!")
        db.session.add(user)
        db.session.commit()
        raw = make_token(user, "verify")
    first = client.get(f"/auth/verify/{raw}", follow_redirects=True)
    second = client.get(f"/auth/verify/{raw}", follow_redirects=True)
    assert b"Email verified" in first.data
    assert b"invalid or expired" in second.data
    with app.app_context():
        assert User.query.filter_by(email="verify@example.com").one().is_verified


def test_login_and_logout(client, verified_user):
    response = client.post("/auth/login", data={"email": "owner@example.com", "password": "StrongPassword123!"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Good morning" in response.data
    response = client.post("/auth/logout", follow_redirects=True)
    assert b"securely logged out" in response.data


def test_bad_logins_temporarily_lock_account(client, app, verified_user):
    for _ in range(5):
        client.post("/auth/login", data={"email": "owner@example.com", "password": "wrong-password"})
    with app.app_context():
        user = User.query.filter_by(email="owner@example.com").one()
        assert user.locked_until is not None


def test_password_reset_is_single_use(client, app, verified_user):
    with app.app_context():
        user = db.session.get(User, verified_user)
        raw = make_token(user, "reset", 1)
    response = client.post(f"/auth/reset-password/{raw}", data={"password": "NewPassword123!", "confirm_password": "NewPassword123!"}, follow_redirects=True)
    assert b"Password updated" in response.data
    response = client.post(f"/auth/reset-password/{raw}", data={"password": "OtherPassword123!", "confirm_password": "OtherPassword123!"}, follow_redirects=True)
    assert b"invalid or expired" in response.data
    with app.app_context():
        assert db.session.get(User, verified_user).check_password("NewPassword123!")
