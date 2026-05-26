# activitypub-inbox-outbox Specification

## ADDED Requirements

### Requirement: Shared inbox
The system SHALL offer a shared inbox endpoint at `/api/v1/activitypub/inbox` that accepts POST requests with ActivityPub activities. Activity types SHALL include at minimum: Follow, Accept, Reject, Undo, Create, Delete, Announce.

#### Scenario: Receive Follow activity (auto-accept)
- GIVEN a remote actor sends a Follow activity targeting a local user
- WHEN the inbox receives the POST
- THEN the system validates the HTTP Signature
- AND an Accept activity is generated and added to the outbox
- AND the follow relationship is established immediately (status: accepted)

#### Scenario: Receive Accept activity
- GIVEN a local user sent a Follow request to a remote actor
- WHEN the inbox receives an Accept activity
- THEN the system marks the remote follow relationship as accepted
- AND the remote actor is added to the local user's following collection

#### Scenario: Receive Reject activity
- GIVEN a local user sent a Follow request to a remote actor
- WHEN the inbox receives a Reject activity
- THEN the follow request is marked as rejected
- AND no follow relationship is established

#### Scenario: Receive Undo-Follow activity
- GIVEN an existing follow relationship with a remote actor
- WHEN the inbox receives an Undo activity referencing the original Follow
- THEN the follow relationship is removed

#### Scenario: Receive Create activity (bookmark shared)
- GIVEN a remote actor posts a Create(Note) activity
- WHEN the inbox receives it
- THEN the Note object is stored as a federated bookmark for the local user's timeline

#### Scenario: Invalid activity signature
- WHEN the inbox receives a POST with an invalid or missing HTTP Signature
- THEN a 401 Unauthorized response is returned
- AND the activity is not processed

### Requirement: Outbox for publishing
Every user SHALL have an outbox endpoint at their actor's outbox URL that returns a paginated list of activities they've published. Activities SHALL include: Create (when adding a public bookmark), Announce (when resharing), and Delete.

#### Scenario: View user outbox
- WHEN a request is made to a user's outbox URL
- THEN the response is an OrderedCollection of the user's recent activities
- AND activities are ordered by creation date (newest first)
- AND content negotiation uses `application/activity+json` for ActivityPub clients

#### Scenario: Public bookmark generates Create activity
- GIVEN a user adds a new bookmark with visibility `public`
- WHEN the bookmark is saved
- THEN a Create(Article) activity is added to the user's outbox
- AND the activity is queued for delivery to all followers' inboxes

#### Scenario: Bookmark deletion generates Delete activity
- GIVEN a user deletes a previously public bookmark
- WHEN the bookmark is deleted
- THEN a Delete activity referencing the bookmark's object ID is added to the outbox
- AND the activity is queued for delivery to followers

### Requirement: Celery background delivery
Outgoing activities SHALL be delivered via Celery background tasks with retry logic. Delivery SHALL use HTTP Signatures for authentication.

#### Scenario: Activity delivered to follower inbox
- GIVEN a public bookmark is created
- WHEN the delivery task runs
- THEN the Create activity is POSTed to each follower's inbox URL with proper HTTP Signature headers
- AND `Content-Type: application/activity+json` is set

#### Scenario: Delivery retry on failure
- GIVEN a delivery attempt fails (network error, 5xx)
- WHEN the task runs again
- THEN it retries up to 5 times with exponential backoff (1m, 5m, 15m, 1h, 6h)
- AND after all retries fail, the delivery is marked as `failed` in the delivery queue

#### Scenario: Deliveries not sent for private bookmarks
- GIVEN a user creates a bookmark with visibility `private`
- WHEN the bookmark is saved
- THEN no activity is added to the outbox
- AND no delivery is queued