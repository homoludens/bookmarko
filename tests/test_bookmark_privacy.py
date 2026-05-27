"""Tests for bookmark privacy controls (visibility)."""
from __future__ import annotations

import pytest

from flaskmarks import create_app
from flaskmarks.models import User, Mark
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


def _create_mark(owner, visibility="private", title="Test Mark"):
    """Create a test mark."""
    m = Mark(owner_id=owner.id)
    m.title = title
    m.url = f"http://example.com/{title.lower().replace(' ', '-')}"
    m.type = "bookmark"
    m.visibility = visibility
    db.session.add(m)
    db.session.commit()
    return m


class TestDefaultVisibility:
    """Task 3.2: Default visibility on user registration."""

    def test_new_user_default_is_private(self, app):
        """A new user's default_bookmark_visibility should be 'private'."""
        with app.app_context():
            u = _create_test_user("default_test")
            assert u.default_bookmark_visibility == "private"

    def test_user_can_change_default(self, app):
        """A user can change their default bookmark visibility."""
        with app.app_context():
            u = _create_test_user("change_default")
            u.default_bookmark_visibility = "public"
            db.session.add(u)
            db.session.commit()
            db.session.refresh(u)
            assert u.default_bookmark_visibility == "public"


class TestBookmarkCreationVisibility:
    """Task 3.1: Bookmarks created with correct visibility."""

    def test_mark_created_with_explicit_public(self, app):
        """Bookmark created with visibility='public' is stored as public."""
        with app.app_context():
            u = _create_test_user("pub_owner")
            m = _create_mark(u, visibility="public", title="Public Mark")
            assert m.visibility == "public"

    def test_mark_created_with_explicit_private(self, app):
        """Bookmark created with visibility='private' is stored as private."""
        with app.app_context():
            u = _create_test_user("priv_owner")
            m = _create_mark(u, visibility="private", title="Private Mark")
            assert m.visibility == "private"

    def test_mark_default_uses_user_default(self, app):
        """Bookmark created without explicit visibility uses user's default."""
        with app.app_context():
            u = _create_test_user("default_mark")
            m = Mark(owner_id=u.id)
            m.title = "Default Private"
            m.url = "http://example.com/default-private"
            m.type = "bookmark"
            db.session.add(m)
            db.session.commit()
            assert m.visibility == "private"


class TestVisibilityFiltering:
    """Task 3.3: Visibility filtering in queries."""

    def test_owner_sees_all_marks(self, app):
        """Owner sees both public and private bookmarks."""
        with app.app_context():
            u = _create_test_user("owner_all")
            _create_mark(u, visibility="public", title="Pub")
            _create_mark(u, visibility="private", title="Priv")
            marks = u.my_marks().all()
            titles = [m.title for m in marks]
            assert "Pub" in titles
            assert "Priv" in titles

    def test_visible_marks_owner_sees_all(self, app):
        """visible_marks with viewer_id=owner returns all."""
        with app.app_context():
            u = _create_test_user("vis_owner")
            _create_mark(u, visibility="public", title="Pub")
            _create_mark(u, visibility="private", title="Priv")
            marks = u.visible_marks(viewer_id=u.id).all()
            assert len(marks) == 2

    def test_visible_marks_non_owner_only_public(self, app):
        """visible_marks with different viewer_id returns only public."""
        with app.app_context():
            owner = _create_test_user("vis_owner2")
            viewer = _create_test_user("vis_viewer")
            _create_mark(owner, visibility="public", title="Pub")
            _create_mark(owner, visibility="private", title="Priv")
            marks = owner.visible_marks(viewer_id=viewer.id).all()
            titles = [m.title for m in marks]
            assert "Pub" in titles
            assert "Priv" not in titles

    def test_visible_marks_no_viewer_only_public(self, app):
        """visible_marks with no viewer_id returns only public."""
        with app.app_context():
            u = _create_test_user("vis_no_viewer")
            _create_mark(u, visibility="public", title="Pub")
            _create_mark(u, visibility="private", title="Priv")
            marks = u.visible_marks().all()
            titles = [m.title for m in marks]
            assert "Pub" in titles
            assert "Priv" not in titles


class TestAPIVisibility:
    """Task 3.5: API enforces visibility."""

    def test_api_serializes_visibility(self, app):
        """API serialization includes visibility field."""
        with app.app_context():
            u = _create_test_user("api_serialize")
            m = _create_mark(u, visibility="public", title="API Serialize")
            from flaskmarks.api.serializers import serialize_mark
            data = serialize_mark(m)
            assert "visibility" in data
            assert data["visibility"] == "public"