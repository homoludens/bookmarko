## 1. Schema Migrations

- [ ] 1.1 Add `visibility` column to `Mark` model (String, default `'private'`). Run `flask db migrate -m "add visibility to marks"` and `flask db upgrade`. `Complexity: Low`
- [ ] 1.2 Add federation columns to `User` model: `actor_id`, `private_key_pem`, `public_key_pem`, `inbox_url`, `outbox_url`, `followers_url`, `following_url`, `default_bookmark_visibility` (default `'private'`). Run `flask db migrate -m "add federation columns to users"` and upgrade. `Complexity: Low`
- [ ] 1.3 Create `Follow` model and table: `id`, `follower_id` (FK->users), `followed_id` (FK->users, nullable for remote), `remote_actor_id` (URL string, nullable for local), `remote_inbox_url`, `status` (accepted/rejected), `created`, `updated`. Run migration. `Complexity: Middle`
- [ ] 1.4 Create `Activity` model and table: `id`, `actor_id` (FK->users), `activity_type` (Create/Follow/Accept/Delete/Announce), `object_json` (JSON), `object_id` (URL string), `target_id` (optional), `created`. Run migration. `Complexity: Middle`
- [ ] 1.5 Create `DeliveryQueue` model and table: `id`, `activity_id` (FK->activities), `inbox_url` (string), `status` (pending/delivered/failed), `retries` (int, default 0), `max_retries` (int, default 5), `last_error` (text), `created`, `updated`. Run migration. `Complexity: Middle`

## 2. User Actor Profiles

- [ ] 2.1 Generate RSA key pair on user registration, store PEM-encoded keys on User model. `Complexity: Middle`
- [ ] 2.2 Implement actor JSON-LD endpoint at `/api/v1/activitypub/actor/<username>` with proper ActivityPub Person shape (id, type, preferredUsername, inbox, outbox, followers, following, publicKey). `Complexity: Middle`
- [ ] 2.3 Implement `/.well-known/webfinger` endpoint resolving `acct:username@domain` to actor URL. `Complexity: Middle`
- [ ] 2.4 Implement `/.well-known/nodeinfo` and NodeInfo 2.0 document endpoint. `Complexity: Low`
- [ ] 2.5 Write tests for actor generation, WebFinger resolution, and NodeInfo. `Complexity: Middle`

## 3. Bookmark Privacy Controls

- [ ] 3.1 Add `visibility` dropdown to bookmark creation/edit forms. `Complexity: Low`
- [ ] 3.2 Add `default_bookmark_visibility` setting to user profile page. `Complexity: Low`
- [ ] 3.3 Filter bookmarks by visibility in all Mark query methods (respect owner vs non-owner). `Complexity: Middle`
- [ ] 3.4 Add visibility indicator icon in bookmark list UI (globe for public, lock for private). `Complexity: Low`
- [ ] 3.5 Enforce visibility in REST API v1 endpoints (marks list, get by id, search). `Complexity: Middle`
- [ ] 3.6 Write tests for visibility filtering, defaults, and API enforcement. `Complexity: Middle`

## 4. Same-Instance Follow Relationships

- [ ] 4.1 Create follow endpoint (POST to follow a user on same instance, auto-accept). `Complexity: Middle`
- [ ] 4.2 Create unfollow endpoint. `Complexity: Low`
- [ ] 4.3 Display follower/following counts and lists on user profile page. `Complexity: Middle`
- [ ] 4.4 Add Follow/Unfollow button on user profile pages (toggle state based on current relationship). `Complexity: Low`
- [ ] 4.5 Add follower/following ActivityPub Collection endpoints. `Complexity: Middle`
- [ ] 4.6 Write tests for local follow/unfollow flows. `Complexity: Middle`

## 5. Public Profile & Fediverse Pages

- [ ] 5.1 Create public user profile page at `/user/<username>` showing bio, public bookmarks, follower/following counts. `Complexity: Middle`
- [ ] 5.2 Implement content negotiation: serve HTML for browsers, `application/activity+json` for fediverse clients. `Complexity: Middle`
- [ ] 5.3 Implement bookmark ActivityPub Object endpoint at `/api/v1/activitypub/objects/<id>` with type Article, title, URL, description, tags, published date. `Complexity: Middle`
- [ ] 5.4 Wire outbox as OrderedCollection of Create activities for public bookmarks. `Complexity: Middle`
- [ ] 5.5 Write tests for content negotiation, object serialization, outbox pagination. `Complexity: Middle`

## 6. ActivityPub Inbox & Outbox

- [ ] 6.1 Implement shared inbox POST handler at `/api/v1/activitypub/inbox` dispatching by activity type (Follow, Accept, Reject, Undo, Create). `Complexity: High`
- [ ] 6.2 Add activity type validation and dispatch in inbox handler. `Complexity: Middle`
- [ ] 6.3 Implement outbound activity creation: Create activity when public bookmark saved, Delete activity when deleted. `Complexity: Middle`
- [ ] 6.4 Create Celery task for outbound delivery: POST to inbox URL with HTTP Signature. `Complexity: High`
- [ ] 6.5 Implement delivery retry logic with exponential backoff via Celery retry. `Complexity: Middle`
- [ ] 6.6 Write tests for inbox activity processing, outbook activity generation, delivery task. `Complexity: High`

## 7. Cross-Instance Federation (Remote)

- [ ] 7.1 Implement HTTP Signatures: sign outgoing requests, verify incoming requests. `Complexity: High`
- [ ] 7.2 Implement remote actor resolution: fetch remote actor JSON-LD, cache for 1 hour. `Complexity: Middle`
- [ ] 7.3 Implement follow-by-handle: parse `@user@domain`, WebFinger lookup, resolve actor, send Follow to remote inbox. `Complexity: High`
- [ ] 7.4 Handle incoming remote Follow activities: create follow record, auto-Accept or prompt user. `Complexity: Middle`
- [ ] 7.5 Implement rate limiting for outgoing deliveries (1 req/sec per remote instance). `Complexity: Low`
- [ ] 7.6 Write tests for HTTP Signature round-trip, remote actor resolution, remote follow flow. `Complexity: High`

## 8. Admin & Debugging

- [ ] 8.1 Add federation status page (connected remote instances, pending deliveries, failed deliveries). `Complexity: Middle`
- [ ] 8.2 Add structured logging for all federation requests (incoming and outgoing). `Complexity: Low`
- [ ] 8.3 Add `/api/v1/activitypub/debug` curl-friendly endpoint for manual testing. `Complexity: Low`
- [ ] 8.4 Add Celery beat periodic cleanup task for old delivered activities and delivery records. `Complexity: Low`