## Context

Flaskmarks is a Flask-based bookmark management app with SQLAlchemy models (User, Mark, Tag), a Jinja2 frontend, and a REST API v1. The app currently has no social features — bookmarks are per-user private. Adding ActivityPub federation introduces a fundamentally new capability: users become public actors, bookmarks can be shared, and instances communicate via standard ActivityPub protocol.

This is a greenfield addition. No existing code needs to be refactored, but the existing User and Mark models need extensions, and the routing needs new ActivityPub-spec endpoints.

## Goals / Non-Goals

**Goals:**
- Users have ActivityPub actor profiles (WebFinger-discoverable)
- Users can follow each other on the same instance (local follows)
- Users can follow remote users across the fediverse (remote follows)
- Bookmarks have public/private visibility controls with user-configurable defaults
- Public bookmarks appear as ActivityPub objects in the user's outbox
- Activities (Create/Delete) are delivered to followers via Celery background tasks with HTTP Signatures
- Public profile pages serve HTML to browsers and ActivityStreams JSON to fediverse clients

**Non-Goals:**
- Full ActivityPub Client-to-Server protocol (C2S) — this is server-to-server only (S2S)
- Bookmark editing/updating via Update activities (can be added later)
- Direct messages or private bookmark sharing between specific users
- Full Mastodon API compatibility (only ActivityPub S2S)
- Media attachments, polls, or rich content types beyond bookmarks
- Real-time streaming (WebSocket/Mastodon streaming API)

## Decisions

1. **Phase: local-first, then remote.**
   - Decision: Implement same-instance following first, then cross-instance federation.
   - Rationale: Local follows are simpler (no HTTP Signatures, no remote actor resolution) and provide a testbed. Cross-instance builds on the same Follow model.
   - Alternative considered: Implement both at once; rejected because debugging remote federation without local working would multiply complexity.

2. **Auto-accept follows (no pending/approval workflow).**
   - Decision: All follows SHALL be auto-accepted immediately. No pending/accept/reject workflow.
   - Rationale: Simpler implementation and better UX for a bookmarking app. Users can still unfollow or block. Accept/Reject can be added later as an opt-in feature.
   - Alternative considered: Full pending/accept/reject workflow with UI; rejected as over-engineering for v1. Users expect social bookmarking to be low-friction.

3. **Visibility column on Mark, not separate model.**
   - Decision: Add `visibility` column to the existing `Mark` model with values `public` / `private`.
   - Rationale: Simple, no extra joins, minimal schema change. Default stored on the User model (`default_bookmark_visibility`).
   - Alternative considered: Separate `BookmarkVisibility` or RBAC model; rejected as over-engineering for two states.

4. **Shared inbox, not per-user inboxes.**
   - Decision: Use a shared inbox at `/api/v1/activitypub/inbox` plus per-user inboxes at each actor URL.
   - Rationale: ActivityPub allows shared inboxes, and this simplifies deployment (single endpoint). Per-user inboxes required by spec but can redirect to shared.
   - Alternative considered: Per-user inboxes only; rejected because multiple inbox delivery would be slower for bulk federated activity.

5. **Celery for delivery, not in-process.**
   - Decision: Use existing Celery configuration for outbound delivery tasks with retry/exponential backoff.
   - Rationale: Celery is already configured in the project (`flaskmarks/core/rag/tasks.py` pattern). In-process delivery would block the web worker and has no retry.
   - Alternative considered: Inline delivery with `threading`; rejected because no retry, no persistence, and blocks request-response cycle.

6. **4096-bit RSA keys, stored in User model.**
   - Decision: Generate RSA key pair on user registration, store PEM-encoded keys in new columns on the `User` model.
   - Rationale: ActivityPub HTTP Signatures require asymmetric keys. 4096-bit is standard for fediverse software. Storing on User model avoids a separate model.
   - Alternative considered: Ed25519 keys (smaller) — some fediverse software doesn't support them. Considered acceptable but RSA is more widely compatible.

7. **Database-backed delivery queue.**
   - Decision: Use a `DeliveryQueue` model (activity_id, inbox_url, status, retries, last_error) rather than Celery's built-in result backend.
   - Rationale: Visibility into delivery status, easy admin UI for troubleshooting, survives worker restarts.
   - Alternative considered: Pure Celery task chain; rejected because debugging failed deliveries is harder without a visible queue.

8. **`application/activity+json` content negotiation.**
   - Decision: Use Flask's `request.accept_mimetypes` to serve HTML vs ActivityStreams JSON from the same URL.
   - Rationale: Follows ActivityPub spec, avoids URL bifurcation. Mastodon/Lemmy fetch actor objects with Accept headers.
   - Alternative considered: Separate URLs for HTML and JSON; rejected as non-standard.

9. **Alembic/Flask-Migrate for all schema changes.**
   - Decision: Every model change SHALL use `flask db migrate` to auto-generate a migration, then `flask db upgrade` to apply. Migrations are in `migrations/versions/`.
   - Rationale: The project already has Flask-Migrate wired up. Auto-generated migrations capture the full diff from current state. Manual migration writing needed only for data backfills or complex column transformations.
   - Note: Run `flask db migrate -m "add fediverse support"` after model changes to generate migration.

## Risks / Trade-offs

- [**Federation debugging is notoriously hard**] → Mitigation: ship `curl`-friendly actor/inspect endpoints and enable structured logging for all federation requests/responses. Add a `/api/v1/activitypub/debug` page for admin diagnosis.
- [**HTTP Signatures are complex to implement correctly**] → Mitigation: use well-tested Python libraries (`activitypub-http-signature` or `pycryptodome`-based implementation). Test against Mastodon test instances.
- [**Outbound delivery can create load on small instances**] → Mitigation: rate-limit per-instance deliveries (1 req/sec default), configurable via settings.
- [**Private key security in database**] → Mitigation: encrypt private keys at rest using application-level encryption (Flask SECRET_KEY derived), not just database-level. Log any attempt to expose via API.
- [**Spam/abuse from open federation**] → Mitigation: require valid HTTP Signatures for inbox writes, reject unknown actors, provide mod tools to block remote instances.
- [**Database growth from activities and delivery queue**] → Mitigation: periodic cleanup of old delivered activities (>90 days) and completed delivery records via Celery beat.

## Migration Plan

1. Add `visibility` column to `Mark` model (default: `'private'`), add `default_bookmark_visibility`, `actor_id`, `private_key_pem`, `public_key_pem` columns to `User` model — run `flask db migrate`
2. Create `Follow`, `Activity`, `DeliveryQueue` models — run `flask db migrate`
3. Create `user-actor-profiles` — WebFinger, actor JSON, key generation on registration, NodeInfo
4. Create `bookmark-privacy-controls` — enforce visibility in views and API, UI indicators, default setting
5. Create `follow-relationships` (local-only, auto-accept) — Follow model, follow/unfollow UI, follower/following collections
6. Create `activitypub-inbox-outbox` — shared inbox handler, outbox collection, Celery delivery tasks (stubs for now, wired for local use)
7. Create `fediverse-public-bookmark-page` — public profile page, ActivityPub object representation, content negotiation
8. Create `cross-instance-federation` — HTTP Signatures, remote actor resolution, WebFinger-based follow by handle, rate limiting

Rollback per capability — each capability is independently revertible by reverting its schema migration and code changes.

## Open Questions

- Should we encrypt private keys at rest? (Yes — use app SECRET_KEY derived encryption)
- What visibility levels beyond public/private might we need? (unlisted for now — scope-limited)
- Should we support remote instances blocking? (Yes — store instance blocklist in config or DB)
- How to handle GDPR/right-to-be-forgotten with federated content? (Delete activity sent to all known followers)
- Should the outbox include only Create(Article) or also Announce (reshare) activities? (Both — Announce for future reshare feature)