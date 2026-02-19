from flask_login import UserMixin

from flaskmarks import create_app


class FakeUser(UserMixin):
    def __init__(self, user_id=1):
        self.id = user_id

    def q_marks_by_url(self, _url):
        return None


class ImportThreadStub:
    def __init__(self, url, user_id):
        self.url = url
        self.user_id = user_id

    def run(self):
        return None


def test_new_mark_request_path_with_title_persists_one_mark(monkeypatch):
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    from flaskmarks.core.extensions import login_manager
    from flaskmarks.views import marks as marks_view

    fake_user = FakeUser()
    login_manager._user_callback = lambda _user_id: fake_user

    captured = {"added": []}

    def fake_add(obj):
        captured["added"].append(obj)

    def fake_commit():
        captured["commits"] = captured.get("commits", 0) + 1

    monkeypatch.setattr(marks_view.db.session, "add", fake_add)
    monkeypatch.setattr(marks_view.db.session, "commit", fake_commit)

    class FailingImportThread:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("Import path should not run when title is provided")

    monkeypatch.setattr(marks_view, "MarksImportThread", FailingImportThread)

    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = str(fake_user.id)
        session["_fresh"] = True

    response = client.post(
        "/mark/new/bookmark",
        data={
            "title": "Example title",
            "url": "https://example.com/path",
            "description": "",
            "tags": "",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/marks/all")
    assert captured.get("commits") == 1
    assert len(captured["added"]) == 1

    created_mark = captured["added"][0]
    assert created_mark.owner_id == fake_user.id
    assert created_mark.type == "bookmark"
    assert created_mark.title == "Example title"
    assert created_mark.url == "https://example.com/path"


def test_new_mark_request_path_without_optional_fields_persists_defaults(monkeypatch):
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    from flaskmarks.core.extensions import login_manager
    from flaskmarks.views import marks as marks_view

    fake_user = FakeUser()
    login_manager._user_callback = lambda _user_id: fake_user

    captured = {"added": []}

    def fake_add(obj):
        captured["added"].append(obj)

    def fake_commit():
        captured["commits"] = captured.get("commits", 0) + 1

    monkeypatch.setattr(marks_view.db.session, "add", fake_add)
    monkeypatch.setattr(marks_view.db.session, "commit", fake_commit)
    monkeypatch.setattr(marks_view, "MarksImportThread", ImportThreadStub)

    client = app.test_client()
    with client.session_transaction() as session:
        session["_user_id"] = str(fake_user.id)
        session["_fresh"] = True

    response = client.post(
        "/mark/new/bookmark",
        data={
            "url": "https://example.org/no-optional-fields",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/marks/all")
    assert captured.get("commits") == 1
    assert len(captured["added"]) == 1

    created_mark = captured["added"][0]
    assert created_mark.owner_id == fake_user.id
    assert created_mark.type == "bookmark"
    assert created_mark.url == "https://example.org/no-optional-fields"
    assert created_mark.title == "https://example.org/no-optional-fields"
