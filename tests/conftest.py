"""Shared pytest fixtures for regression test suites."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pytest
from flask_login import UserMixin

from flaskmarks import create_app


@dataclass
class FakeMark:
    id: int = 1
    title: str = "Example"
    clicks: int = 0


class FakeUser(UserMixin):
    def __init__(self, user_id: int = 1, mark: FakeMark | None = None):
        self.id = user_id
        self._mark = mark or FakeMark()

    def q_marks_by_url(self, _url):
        return None

    def get_mark_by_id(self, mark_id):
        if int(mark_id) == self._mark.id:
            return self._mark
        return None


class FakeScopedStatus:
    def __init__(self, payload: dict):
        self._payload = payload

    def as_dict(self):
        return dict(self._payload)


@pytest.fixture
def app():
    application = create_app()
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return application


@pytest.fixture
def csrf_app():
    application = create_app()
    application.config.update(TESTING=True, WTF_CSRF_ENABLED=True)
    return application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def login_session() -> Callable:
    def _login(client, user_id: int):
        with client.session_transaction() as session:
            session["_user_id"] = str(user_id)
            session["_fresh"] = True

    return _login
