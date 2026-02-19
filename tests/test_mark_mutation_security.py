from flask_login import UserMixin

from flaskmarks import create_app


class FakeMark:
    def __init__(self, mark_id=1, title="Example"):
        self.id = mark_id
        self.title = title
        self.clicks = 0


class FakeUser(UserMixin):
    def __init__(self, user_id=1, mark=None):
        self.id = user_id
        self._mark = mark or FakeMark()

    def get_mark_by_id(self, mark_id):
        if int(mark_id) == self._mark.id:
            return self._mark
        return None


def _login(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def test_get_mutation_requests_are_rejected(monkeypatch):
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=True)

    from flaskmarks.core.extensions import login_manager

    fake_user = FakeUser()
    login_manager._user_callback = lambda _user_id: fake_user

    client = app.test_client()
    _login(client, fake_user.id)

    delete_response = client.get(f"/mark/delete/{fake_user._mark.id}")
    inc_response = client.get("/mark/inc", query_string={"id": fake_user._mark.id})

    assert delete_response.status_code == 405
    assert inc_response.status_code == 405


def test_post_mutations_require_csrf_token(monkeypatch):
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=True)

    from flaskmarks.core.extensions import login_manager
    from flaskmarks.views import marks as marks_view

    fake_user = FakeUser()
    login_manager._user_callback = lambda _user_id: fake_user

    captured = {"deleted": 0, "commits": 0}

    def fake_delete(_obj):
        captured["deleted"] += 1

    def fake_commit():
        captured["commits"] += 1

    monkeypatch.setattr(marks_view.db.session, "delete", fake_delete)
    monkeypatch.setattr(marks_view.db.session, "commit", fake_commit)

    client = app.test_client()
    _login(client, fake_user.id)

    delete_response = client.post(f"/mark/delete/{fake_user._mark.id}")
    inc_response = client.post("/mark/inc", data={"id": fake_user._mark.id})

    assert delete_response.status_code == 400
    assert inc_response.status_code == 400
    assert captured["deleted"] == 0
    assert captured["commits"] == 0
    assert fake_user._mark.clicks == 0
