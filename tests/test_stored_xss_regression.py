from flask_login import UserMixin

from flaskmarks import create_app


class FakeMark:
    def __init__(self, mark_id=1, title="Stored HTML", full_html=""):
        self.id = mark_id
        self.title = title
        self.type = "bookmark"
        self.full_html = full_html


class FakeUser(UserMixin):
    def __init__(self, user_id=1, mark=None):
        self.id = user_id
        self._mark = mark or FakeMark()

    def q_marks_by_url(self, _url):
        return None

    def get_mark_by_id(self, mark_id):
        if int(mark_id) == self._mark.id:
            return self._mark
        return None


class ImportThreadStub:
    def __init__(self, *_args, **_kwargs):
        pass

    def run(self):
        return {
            "title": "Imported title",
            "description": "Imported description",
            "full_html": (
                '<h2>Safe title</h2>'
                '<p onclick="alert(1)">Hello <strong>world</strong></p>'
                '<script>alert("xss")</script>'
                '<a href="javascript:alert(2)">bad</a>'
                '<a href="https://example.com">good link</a>'
                '<img src="https://example.com/image.png" onerror="alert(3)" alt="ok">'
            ),
            "tags": [],
        }


def _login(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def test_imported_full_html_payloads_are_neutralized_before_storage(monkeypatch):
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
    _login(client, fake_user.id)

    response = client.post(
        "/mark/new/bookmark",
        data={
            "url": "https://example.org/imported-page",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/marks/all")
    assert captured.get("commits") == 1
    assert len(captured["added"]) == 1

    created_mark = captured["added"][0]
    assert created_mark.title == "Imported title"
    assert created_mark.description == "Imported description"

    sanitized = created_mark.full_html
    assert "<script" not in sanitized
    assert "onclick" not in sanitized
    assert "onerror" not in sanitized
    assert "javascript:" not in sanitized
    assert "<h2>Safe title</h2>" in sanitized
    assert "<strong>world</strong>" in sanitized
    assert '<a href="https://example.com">good link</a>' in sanitized


def test_view_html_escapes_stored_markup_in_iframe_srcdoc():
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    from flaskmarks.core.extensions import login_manager

    fake_mark = FakeMark(
        mark_id=7,
        full_html='<script>alert("xss")</script><p onclick="alert(1)">hello</p>',
    )
    fake_user = FakeUser(mark=fake_mark)
    login_manager._user_callback = lambda _user_id: fake_user

    client = app.test_client()
    _login(client, fake_user.id)

    response = client.get(f"/mark/viewhtml/{fake_mark.id}")

    assert response.status_code == 200
    body = response.get_data(as_text=True)

    assert 'sandbox=""' in body
    assert '&lt;script&gt;alert(&#34;xss&#34;)&lt;/script&gt;' in body
    assert '<script>alert("xss")</script>' not in body

