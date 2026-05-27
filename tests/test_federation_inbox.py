"""Tests for ActivityPub inbox handling and delivery infrastructure."""
from __future__ import annotations

import json
import os

import pytest

# Must set test DB env before importing app
os.environ["FLASKMARKS_TEST_DB"] = "sqlite"

from flaskmarks import create_app
from flaskmarks.models import User, Follow, DeliveryQueue, Activity
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

    # Override 404 handler to return plain 404s instead of redirects
    @application.errorhandler(404)
    def plain_404(error):
        return "Not Found", 404

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
    # Return user_id so we can re-query within new contexts
    return u.id


def _get_user(user_id):
    """Get a user by ID, re-querying from the current session."""
    return User.query.get(user_id)


class TestInbox:
    """Tests for the ActivityPub inbox endpoints."""

    INBOX_URL = "/api/v1/activitypub/inbox"

    def _post_activity(self, client, body):
        """Helper: POST JSON to shared inbox."""
        return client.post(
            self.INBOX_URL,
            data=json.dumps(body),
            content_type="application/activity+json",
        )

    def test_inbox_accepts_follow(self, client, app):
        """Follow activity creates a Follow record and returns 202."""
        alice_id = None
        alice_actor_id = None
        with app.app_context():
            alice_id = _create_test_user("alice")
            alice = _get_user(alice_id)
            alice_actor_id = alice.actor_id

        activity = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "Follow",
            "actor": "http://remote.instance/actor/bob",
            "object": alice_actor_id,
            "id": "http://remote.instance/activities/123",
        }

        response = self._post_activity(client, activity)
        assert response.status_code == 202

        with app.app_context():
            follow = Follow.query.filter_by(
                remote_actor_id="http://remote.instance/actor/bob",
                followed_id=alice_id,
            ).first()
            assert follow is not None
            assert follow.status == "accepted"

    def test_inbox_returns_202(self, client, app):
        """All valid activities return 202 Accepted (ActivityPub convention)."""
        with app.app_context():
            _create_test_user("alice")

        # Test with a Create activity
        activity = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "Create",
            "actor": "http://remote.instance/actor/bob",
            "object": {
                "id": "http://remote.instance/objects/1",
                "type": "Note",
                "content": "Hello!",
            },
        }

        response = self._post_activity(client, activity)
        assert response.status_code == 202

        # Test with an unknown activity type
        unknown = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "UnknownType",
            "actor": "http://remote.instance/actor/bob",
            "object": "http://example.com/something",
        }

        response = self._post_activity(client, unknown)
        assert response.status_code == 202

    def test_inbox_rejects_no_type(self, client, app):
        """Activity without 'type' or 'actor' fields should be rejected."""
        # Missing type
        response = client.post(
            self.INBOX_URL,
            data=json.dumps({"actor": "http://example.com/actor"}),
            content_type="application/activity+json",
        )
        assert response.status_code == 400

        # Missing actor
        response = client.post(
            self.INBOX_URL,
            data=json.dumps({"type": "Follow"}),
            content_type="application/activity+json",
        )
        assert response.status_code == 400

        # Invalid JSON
        response = client.post(
            self.INBOX_URL,
            data="not-json",
            content_type="application/activity+json",
        )
        assert response.status_code == 400

    def test_user_inbox_delegates_to_shared(self, client, app):
        """Per-user inbox delegates to shared inbox logic."""
        alice_id = None
        alice_actor_id = None
        with app.app_context():
            alice_id = _create_test_user("alice")
            alice = _get_user(alice_id)
            alice_actor_id = alice.actor_id

        activity = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "Follow",
            "actor": "http://remote.instance/actor/bob",
            "object": alice_actor_id,
        }

        response = client.post(
            f"/api/v1/activitypub/actor/alice/inbox",
            data=json.dumps(activity),
            content_type="application/activity+json",
        )
        assert response.status_code == 202

        with app.app_context():
            follow = Follow.query.filter_by(
                remote_actor_id="http://remote.instance/actor/bob"
            ).first()
            assert follow is not None

    def test_user_inbox_404_for_unknown(self, client, app):
        """Per-user inbox returns 404 for nonexistent user."""
        activity = {
            "@context": "https://www.w3.org/ns/activitystreams",
            "type": "Follow",
            "actor": "http://remote.instance/actor/bob",
            "object": "http://test.local/api/v1/activitypub/actor/nobody",
        }

        response = client.post(
            "/api/v1/activitypub/actor/nobody/inbox",
            data=json.dumps(activity),
            content_type="application/activity+json",
        )
        assert response.status_code == 404


class TestDeliveryQueue:
    """Tests for the outbound delivery queue."""

    def test_enqueue_delivery_creates_record(self, app):
        """enqueue_delivery creates a DeliveryQueue entry."""
        from flaskmarks.core.activitypub_delivery import enqueue_delivery

        with app.app_context():
            alice_id = _create_test_user("alice")

            activity = Activity(
                actor_id=alice_id,
                activity_type='Create',
                object_json='{"id": "1", "type": "Article"}',
                object_id='1',
            )
            db.session.add(activity)
            db.session.commit()

            enqueue_delivery(activity, "http://remote.instance/actor/bob/inbox")

            delivery = DeliveryQueue.query.filter_by(
                activity_id=activity.id
            ).first()
            assert delivery is not None
            assert delivery.inbox_url == "http://remote.instance/actor/bob/inbox"
            assert delivery.status == "pending"
            assert delivery.retries == 0
            assert delivery.max_retries == 5

    def test_enqueue_delivery_skips_without_inbox(self, app):
        """enqueue_delivery with no inbox_url does not create a record."""
        from flaskmarks.core.activitypub_delivery import enqueue_delivery

        with app.app_context():
            alice_id = _create_test_user("alice")

            activity = Activity(
                actor_id=alice_id,
                activity_type='Create',
                object_json='{"id": "1", "type": "Article"}',
                object_id='1',
            )
            db.session.add(activity)
            db.session.commit()

            # Call with None inbox_url - should not create a record
            enqueue_delivery(activity, None)

            count = DeliveryQueue.query.filter_by(
                activity_id=activity.id
            ).count()
            assert count == 0
