from flask_login import UserMixin
import pytest

from flaskmarks import create_app


class _FakeUser(UserMixin):
    def __init__(self, user_id):
        self.id = user_id


class _FakeScopedStatus:
    def __init__(self, payload):
        self._payload = payload

    def as_dict(self):
        return dict(self._payload)


def _login(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def test_startup_fails_in_production_without_required_env(monkeypatch):
    class ProductionConfig:
        ENV = "production"
        SECRET_KEY = "explicit-test-secret"
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("FLASK_DEBUG", raising=False)
    monkeypatch.delenv("ALLOW_PRODUCTION_DEBUG", raising=False)

    with pytest.raises(RuntimeError, match="Missing required production configuration"):
        create_app(ProductionConfig)


def test_startup_fails_in_production_with_insecure_secret(monkeypatch):
    class ProductionConfig:
        ENV = "production"
        SECRET_KEY = "super-duper-secret-key-CHANGE-ME"
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

    monkeypatch.setenv("FLASK_SECRET_KEY", "configured-secret")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.delenv("FLASK_DEBUG", raising=False)
    monkeypatch.delenv("ALLOW_PRODUCTION_DEBUG", raising=False)

    with pytest.raises(
        RuntimeError,
        match="FLASK_SECRET_KEY must be explicitly configured",
    ):
        create_app(ProductionConfig)


def test_import_status_is_isolated_by_user_for_same_job_id(monkeypatch):
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    from flaskmarks.core.extensions import login_manager
    from flaskmarks.views import marks as marks_view

    login_manager._user_callback = lambda user_id: _FakeUser(int(user_id))

    scoped_rows = {
        (1, "shared-job"): _FakeScopedStatus(
            {"job_id": "shared-job", "status": 1, "total_lines": 3, "complete": False}
        ),
        (2, "shared-job"): _FakeScopedStatus(
            {"job_id": "shared-job", "status": 3, "total_lines": 3, "complete": True}
        ),
    }

    def fake_get_import_job_status(user_id, job_id=None):
        return scoped_rows.get((user_id, job_id))

    monkeypatch.setattr(marks_view, "get_import_job_status", fake_get_import_job_status)

    client_a = app.test_client()
    _login(client_a, user_id=1)
    response_a = client_a.get("/marks/import/status", query_string={"job_id": "shared-job"})

    client_b = app.test_client()
    _login(client_b, user_id=2)
    response_b = client_b.get("/marks/import/status", query_string={"job_id": "shared-job"})

    assert response_a.status_code == 200
    assert response_b.status_code == 200
    assert response_a.get_json()["status"] == 1
    assert response_b.get_json()["status"] == 3


def test_import_status_is_isolated_by_job_for_same_user(monkeypatch):
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    from flaskmarks.core.extensions import login_manager
    from flaskmarks.views import marks as marks_view

    login_manager._user_callback = lambda user_id: _FakeUser(int(user_id))

    scoped_rows = {
        (9, "job-a"): _FakeScopedStatus(
            {"job_id": "job-a", "status": 2, "total_lines": 5, "complete": False}
        ),
        (9, "job-b"): _FakeScopedStatus(
            {"job_id": "job-b", "status": 5, "total_lines": 5, "complete": True}
        ),
    }

    def fake_get_import_job_status(user_id, job_id=None):
        return scoped_rows.get((user_id, job_id))

    monkeypatch.setattr(marks_view, "get_import_job_status", fake_get_import_job_status)

    client = app.test_client()
    _login(client, user_id=9)

    response_a = client.get("/marks/import/status", query_string={"job_id": "job-a"})
    response_b = client.get("/marks/import/status", query_string={"job_id": "job-b"})
    response_missing = client.get("/marks/import/status", query_string={"job_id": "job-c"})

    assert response_a.status_code == 200
    assert response_b.status_code == 200
    assert response_a.get_json()["job_id"] == "job-a"
    assert response_b.get_json()["job_id"] == "job-b"
    assert response_missing.status_code == 404
