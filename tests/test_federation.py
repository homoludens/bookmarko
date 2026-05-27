"""Tests for federation endpoints: bookmark object, outbox, and content negotiation."""
from __future__ import annotations

import os

import pytest

# Must set test DB env before importing app
os.environ["FLASKMARKS_TEST_DB"] = "sqlite"

from flaskmarks import create_app
from flaskmarks.models import User, Mark, Tag
from flaskmarks.core.extensions import db


@pytest.fixture
def app():
    """Create app with in-memory SQLite for tests."""
    application = create_app()
    application.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
    )
    return application


@pytest.fixture(autouse=True)
def _db_tables(app):
    """Create all tables for each test, tear down after."""
    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _create_test_user(username="alice"):
    """Create a test user in the database."""
    from flaskmarks.core.extensions import bcrypt
    u = User()
    u.username = username
    u.email = f"{username}@test.local"
    u.password = bcrypt.generate_password_hash("test123").decode("utf-8")
    u.actor_id = f"http://test.local/api/v1/activitypub/actor/{username}"
    u.inbox_url = f"{u.actor_id}/inbox"
    u.outbox_url = f"{u.actor_id}/outbox"
    u.followers_url = f"{u.actor_id}/followers"
    u.following_url = f"{u.actor_id}/following"
    db.session.add(u)
    db.session.commit()
    return u


def _create_mark(owner, visibility="private", title="Test Mark", description=None):
    """Create a test mark with optional tags."""
    m = Mark(owner_id=owner.id)
    m.title = title
    m.url = f"http://example.com/{title.lower().replace(' ', '-')}"
    m.type = "bookmark"
    m.visibility = visibility
    m.description = description
    m.created = None  # let SQLAlchemy default kick in
    db.session.add(m)
    db.session.commit()
    # Set created explicitly after commit for deterministic isoformat
    from datetime import datetime as dt
    m.created = dt.utcnow()
    db.session.commit()
    return m


def _add_tag_to_mark(mark, tag_name):
    """Add a tag to a mark."""
    tag = Tag.query.filter_by(title=tag_name).first()
    if not tag:
        tag = Tag(tag_name)
        db.session.add(tag)
        db.session.commit()
    mark.tags.append(tag)
    db.session.commit()


class TestBookmarkObject:
    """Tests for the ActivityPub Bookmark Object endpoint."""

    def test_bookmark_object_returns_article(self, client, app):
        """Public mark returns a valid Article object with all required fields."""
        with app.app_context():
            u = _create_test_user("alice")
            m = _create_mark(u, visibility="public", title="Test Article",
                             description="A test description")
            _add_tag_to_mark(m, "testing")
            _add_tag_to_mark(m, "activitypub")
            mark_id = m.id

        response = client.get(f"/api/v1/activitypub/objects/{mark_id}")

        assert response.status_code == 200
        assert response.content_type == "application/activity+json"
        data = response.get_json()

        assert data["@context"] == "https://www.w3.org/ns/activitystreams"
        assert data["type"] == "Article"
        assert data["id"].endswith(f"/api/v1/activitypub/objects/{mark_id}")
        assert data["attributedTo"] == u.actor_id
        assert data["name"] == "Test Article"
        assert data["url"] == "http://example.com/test-article"
        assert data["content"] == "A test description"
        assert "published" in data
        assert "updated" in data

        # Check tags
        assert len(data["tag"]) == 2
        tag_names = {t["name"] for t in data["tag"]}
        assert "#testing" in tag_names
        assert "#activitypub" in tag_names
        for t in data["tag"]:
            assert t["type"] == "Hashtag"

    def test_bookmark_object_404_for_private(self, client, app):
        """Private mark returns 404 from the object endpoint."""
        with app.app_context():
            u = _create_test_user("bob")
            m = _create_mark(u, visibility="private", title="Secret Bookmark")
            mark_id = m.id

        response = client.get(f"/api/v1/activitypub/objects/{mark_id}")

        assert response.status_code == 404

    def test_bookmark_object_404_for_nonexistent(self, client):
        """Nonexistent mark returns 404."""
        response = client.get("/api/v1/activitypub/objects/99999")
        assert response.status_code == 404


class TestOutbox:
    """Tests for the ActivityPub Outbox endpoint."""

    def test_outbox_returns_ordered_collection_page(self, client, app):
        """Outbox returns a valid OrderedCollectionPage of Create activities."""
        with app.app_context():
            u = _create_test_user("alice")
            _create_mark(u, visibility="public", title="Public One")
            _create_mark(u, visibility="public", title="Public Two")

        response = client.get("/api/v1/activitypub/actor/alice/outbox")

        assert response.status_code == 200
        assert response.content_type == "application/activity+json"
        data = response.get_json()

        assert data["@context"] == "https://www.w3.org/ns/activitystreams"
        assert data["type"] == "OrderedCollectionPage"
        assert data["totalItems"] == 2
        assert "partOf" in data
        assert len(data["orderedItems"]) == 2

        # Each item should be a Create activity
        for item in data["orderedItems"]:
            assert item["type"] == "Create"
            assert item["actor"] == u.actor_id
            assert "published" in item
            # The inner object should be an Article
            obj = item["object"]
            assert obj["type"] == "Article"
            assert obj["attributedTo"] == u.actor_id
            assert "name" in obj
            assert "url" in obj
            assert "id" in obj

    def test_outbox_only_includes_public_marks(self, client, app):
        """Private marks should not appear in the outbox."""
        with app.app_context():
            u = _create_test_user("alice")
            _create_mark(u, visibility="public", title="Public Mark")
            _create_mark(u, visibility="private", title="Private Mark")
            _create_mark(u, visibility="public", title="Another Public")

        response = client.get("/api/v1/activitypub/actor/alice/outbox")

        assert response.status_code == 200
        data = response.get_json()
        assert data["totalItems"] == 2
        names = [item["object"]["name"] for item in data["orderedItems"]]
        assert "Public Mark" in names
        assert "Another Public" in names
        assert "Private Mark" not in names

    def test_outbox_pagination(self, client, app):
        """Outbox paginates correctly with ?page and ?page_size."""
        with app.app_context():
            u = _create_test_user("alice")
            for i in range(5):
                _create_mark(u, visibility="public", title=f"Mark {i}")

        # Page 1 with page_size 2
        response = client.get(
            "/api/v1/activitypub/actor/alice/outbox?page=1&page_size=2"
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["totalItems"] == 5
        assert len(data["orderedItems"]) == 2
        assert data["id"].endswith("?page=1")

        # Page 3 with page_size 2 (should have 1 item)
        response = client.get(
            "/api/v1/activitypub/actor/alice/outbox?page=3&page_size=2"
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["totalItems"] == 5
        assert len(data["orderedItems"]) == 1

    def test_outbox_404_for_nonexistent_user(self, client):
        """Outbox returns 404 for unknown user."""
        response = client.get("/api/v1/activitypub/actor/nobody/outbox")
        assert response.status_code == 404


class TestContentNegotiation:
    """Tests for content negotiation on the public profile."""

    def test_public_profile_renders(self, app, client):
        """Public profile renders HTML by default (no Accept header)."""
        with app.app_context():
            u = _create_test_user("alice")

        response = client.get("/user/alice")

        assert response.status_code == 200
        # Should be HTML by default
        assert "text/html" in response.content_type

    def test_public_profile_redirects_for_activity_json(self, app, client):
        """Public profile redirects to actor endpoint when Accept is application/activity+json."""
        with app.app_context():
            _create_test_user("alice")

        response = client.get(
            "/user/alice",
            headers={"Accept": "application/activity+json"},
        )

        # Should be a redirect (302)
        assert response.status_code == 302
        assert "/api/v1/activitypub/actor/alice" in response.location

    def test_public_profile_404_for_nonexistent(self, client):
        """Public profile returns 404 for unknown user."""
        response = client.get("/user/nobody")
        assert response.status_code == 404

    def test_public_profile_html_still_works(self, app, client):
        """Public profile still returns HTML when text/html is explicitly requested."""
        with app.app_context():
            _create_test_user("alice")

        response = client.get(
            "/user/alice",
            headers={"Accept": "text/html"},
        )

        assert response.status_code == 200
        assert "text/html" in response.content_type