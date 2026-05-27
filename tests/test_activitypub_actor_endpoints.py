"""Tests for ActivityPub actor, WebFinger, and NodeInfo endpoints."""
from __future__ import annotations

from unittest.mock import MagicMock

from flaskmarks import create_app


class FakeUser:
    """Fake user for monkeypatching User.query in ActivityPub tests."""
    def __init__(self, username="alice"):
        self.username = username
        self.actor_id = f"http://example.com/api/v1/activitypub/actor/{username}"
        self.public_key_pem = "-----BEGIN PUBLIC KEY-----\nFAKEKEY\n-----END PUBLIC KEY-----"
        self.inbox_url = f"{self.actor_id}/inbox"
        self.outbox_url = f"{self.actor_id}/outbox"
        self.followers_url = f"{self.actor_id}/followers"
        self.following_url = f"{self.actor_id}/following"


class FakeNoUser:
    """Empty query result — no user found."""
    def first(self):
        return None


def _patch_user_query(monkeypatch, query_return):
    """Patch User.query across all relevant import paths.

    The webfinger and nodeinfo endpoints re-import User from flaskmarks.models
    inside the function body, so we must patch both ap.User and the source
    module to cover both import styles.
    """
    import flaskmarks.api.activitypub as ap
    import flaskmarks.models as models

    mock_query = MagicMock()
    mock_query.filter_by.return_value = mock_query
    mock_query.first.return_value = query_return

    # Patch the module-level reference used by actor()
    monkeypatch.setattr(ap, "User", MagicMock())
    monkeypatch.setattr(ap.User, "query", mock_query)

    # Patch the source module so webfinger()/nodeinfo() local import picks it up
    monkeypatch.setattr(models, "User", MagicMock())
    monkeypatch.setattr(models.User, "query", mock_query)


def _patch_user_count(monkeypatch, count):
    """Patch User.query.count() across all import paths."""
    import flaskmarks.api.activitypub as ap
    import flaskmarks.models as models

    mock_query = MagicMock()
    mock_query.count.return_value = count

    monkeypatch.setattr(ap, "User", MagicMock())
    monkeypatch.setattr(ap.User, "query", mock_query)

    monkeypatch.setattr(models, "User", MagicMock())
    monkeypatch.setattr(models.User, "query", mock_query)


def _disable_404_redirect(app):
    """Override the app's 404 handler so it returns 404 instead of redirecting."""
    @app.errorhandler(404)
    def plain_404(error):
        return "Not Found", 404


def test_actor_endpoint_returns_user(monkeypatch):
    """Actor endpoint returns valid JSON-LD for existing user."""
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    client = app.test_client()

    fake_user = FakeUser("alice")

    import flaskmarks.api.activitypub as ap
    mock_query = MagicMock()
    mock_query.filter_by.return_value = mock_query
    mock_query.first.return_value = fake_user
    monkeypatch.setattr(ap, "User", MagicMock())
    monkeypatch.setattr(ap.User, "query", mock_query)

    response = client.get("/api/v1/activitypub/actor/alice")

    assert response.status_code == 200
    data = response.get_json()
    assert data["type"] == "Person"
    assert data["preferredUsername"] == "alice"
    assert data["id"] == "http://example.com/api/v1/activitypub/actor/alice"
    assert data["inbox"] == "http://example.com/api/v1/activitypub/actor/alice/inbox"
    assert data["outbox"] == "http://example.com/api/v1/activitypub/actor/alice/outbox"
    assert data["followers"] == "http://example.com/api/v1/activitypub/actor/alice/followers"
    assert data["following"] == "http://example.com/api/v1/activitypub/actor/alice/following"
    assert "publicKey" in data
    assert data["publicKey"]["publicKeyPem"] == fake_user.public_key_pem
    assert "@context" in data


def test_actor_endpoint_returns_404_for_nonexistent_user(monkeypatch):
    """Actor endpoint returns 404 for unknown user."""
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    _disable_404_redirect(app)
    client = app.test_client()

    import flaskmarks.api.activitypub as ap
    monkeypatch.setattr(ap, "User", MagicMock())
    mock_query = MagicMock()
    mock_query.filter_by.return_value = FakeNoUser()
    monkeypatch.setattr(ap.User, "query", mock_query)

    response = client.get("/api/v1/activitypub/actor/nonexistent")
    assert response.status_code == 404


def test_webfinger_endpoint_resolves_user(monkeypatch):
    """WebFinger returns valid JRD for existing user."""
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    client = app.test_client()

    fake_user = FakeUser("alice")

    _patch_user_query(monkeypatch, fake_user)

    response = client.get("/.well-known/webfinger?resource=acct:alice@localhost")

    assert response.status_code == 200
    data = response.get_json()
    assert data["subject"] == "acct:alice@localhost"
    assert len(data["links"]) > 0
    assert data["links"][0]["rel"] == "self"
    assert data["links"][0]["type"] == "application/activity+json"
    assert data["links"][0]["href"] == fake_user.actor_id


def test_webfinger_returns_404_for_unknown_user(monkeypatch):
    """WebFinger returns 404 for user not found on this instance."""
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    _disable_404_redirect(app)
    client = app.test_client()

    _patch_user_query(monkeypatch, None)

    response = client.get("/.well-known/webfinger?resource=acct:nobody@localhost")
    assert response.status_code == 404


def test_webfinger_returns_400_for_malformed_resource():
    """WebFinger returns 400 for non-acct: resource."""
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    client = app.test_client()

    response = client.get("/.well-known/webfinger?resource=invalid")
    assert response.status_code == 400


def test_nodeinfo_well_known_discovery():
    """NodeInfo discovery returns link to version 2.0."""
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    client = app.test_client()

    response = client.get("/.well-known/nodeinfo")
    assert response.status_code == 200
    data = response.get_json()
    assert "links" in data
    assert any("2.0" in link["href"] for link in data["links"])


def test_nodeinfo_document_structure(monkeypatch):
    """NodeInfo 2.0 document has correct software info and structure."""
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    client = app.test_client()

    _patch_user_count(monkeypatch, 5)

    response = client.get("/api/v1/activitypub/nodeinfo/2.0")
    assert response.status_code == 200
    data = response.get_json()
    assert data["version"] == "2.0"
    assert data["software"]["name"] == "flaskmarks"
    assert "activitypub" in data["protocols"]
    assert data["usage"]["users"]["total"] == 5
    assert data["openRegistrations"] is True