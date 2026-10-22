import pytest

from echoguard import create_app
from echoguard.config import TestConfig
from echoguard.extensions import db
from echoguard.models import User


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.drop_all()
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def verified_user(app):
    with app.app_context():
        user = User(email="owner@example.com", name="Owner", is_verified=True)
        user.set_password("StrongPassword123!")
        db.session.add(user)
        db.session.commit()
        return user.id


def login(client, email="owner@example.com", password="StrongPassword123!"):
    return client.post("/auth/login", data={"email": email, "password": password}, follow_redirects=True)
