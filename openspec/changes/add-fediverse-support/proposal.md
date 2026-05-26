## Why

Flaskmarks is a self-hosted bookmarking app that currently has no social or sharing capabilities. Adding ActivityPub federation lets users share bookmarks across the fediverse, follow other users (on the same instance or remote instances like Mastodon and Lemmy), and discover bookmarks from people they follow. This transforms a single-user tool into a social bookmarking platform.

Enabling same-instance following first provides a clean local testbed before tackling the complexity of cross-instance HTTP Signatures and remote delivery.

## What Changes

- Introduce **ActivityPub Actor profiles** for every user, with webfinger discovery (`@user@domain`)
- Add **follow/unfollow** relationships with auto-accept (no pending/approval workflow) — same-instance first, then cross-instance
- Implement **ActivityPub inbox/outbox** endpoints to send and receive activities
- Add **bookmark visibility controls** (public/private, defaults to private)
- Create **public bookmark pages** rendered as ActivityPub objects readable by remote instances
- Implement **HTTP Signatures** and remote actor resolution for cross-instance federation
- Add database migrations for follows, activities, and privacy columns
- Expose a **NodeInfo** endpoint for fediverse server discovery

## Capabilities

### New Capabilities
- `user-actor-profiles`: ActivityPub actor endpoints (webfinger, actor JSON-LD), per-user actor keys for HTTP Signatures
- `follow-relationships`: Local and remote follow/unfollow, follower/following collections, accept/reject flows
- `activitypub-inbox-outbox`: Shared and personal inboxes for receiving activities, outbox for publishing (Create/Announce/Delete)
- `bookmark-privacy-controls`: Per-bookmark visibility (public/private), user-configurable default visibility, privacy enforcement in views and API
- `fediverse-public-bookmark-page`: Public bookmark profiles and individual bookmark pages rendered as ActivityPub Objects, with HTML+ActivityStreams content negotiation
- `cross-instance-federation`: Remote actor resolution from WebFinger, HTTP Signatures for outgoing delivery, background delivery queue with retry

### Modified Capabilities
- None.

## Impact

- **New dependencies**: ActivityPub HTTP Signatures library (`http-signature` or equivalent), background task runner for delivery (existing Celery config can be used), cryptography libraries (likely already available via Python stdlib or existing deps)
- **New models**: `Follow` (follower_id, followed_id, remote_actor, status, created), `Activity` (actor, type, object, target, created, delivered), `OutboxDelivery` (activity_id, inbox_url, status, retries)
- **Modified models**: `User` (add `actor_id`, `private_key_pem`, `public_key_pem`, `inbox_url`, `outbox_url`, `followers_url`, `following_url`), `Mark` (add `visibility` column with default from user settings)
- **New routes**: `/.well-known/webfinger`, `/.well-known/nodeinfo`, `/api/v1/activitypub/actor/<username>`, `/api/v1/activitypub/inbox`, `/api/v1/activitypub/outbox`, `/api/v1/activitypub/follow/<username>`
- **Modified views**: Profile page (add public profile URL, follower/following counts), bookmark display (respect visibility), registration (add default bookmark visibility setting)
- **Operational**: Instances must have a public domain name for federation to work. New background Celery tasks for outbound delivery and inbox processing.