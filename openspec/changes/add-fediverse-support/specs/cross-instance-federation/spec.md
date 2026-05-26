# cross-instance-federation Specification

## ADDED Requirements

### Requirement: HTTP Signatures for outgoing requests
All outgoing POST requests to remote inboxes SHALL be signed using HTTP Signatures (draft-cavage-http-signatures). The signing key SHALL be the sender's private key with the `(request-target)`, `host`, and `date` headers signed.

#### Scenario: Outgoing request signed
- WHEN a local server sends an activity to a remote inbox
- THEN the `Signature` header is present with `keyId` pointing to the sender's public key URL
- AND the signature covers `(request-target)`, `host`, and `date`
- AND the remote server can verify the signature using the sender's public key

#### Scenario: Incoming request verified
- WHEN the local inbox receives a POST with an HTTP Signature header
- THEN the system fetches the remote actor's public key
- AND verifies the signature
- AND rejects with 401 if verification fails

### Requirement: Remote actor resolution
When processing an incoming Follow activity from a remote server, the system SHALL fetch the remote actor's profile to obtain their inbox URL, public key, and other required fields.

#### Scenario: Remote actor fetched
- GIVEN a remote actor URL `https://remote.example/users/alice`
- WHEN the system needs to verify or deliver to this actor
- THEN a GET request is made to the actor URL with `Accept: application/activity+json`
- AND the response is cached locally for up to 1 hour

#### Scenario: Remote follow resolution flow
- GIVEN user `bob@local.instance`
- WHEN `bob` follows `alice@remote.instance`
- THEN the system resolves `alice`'s actor via WebFinger at `remote.instance`
- AND obtains `alice`'s inbox URL
- AND sends a Follow activity to that inbox

### Requirement: Cross-instance follow request
A user SHALL be able to follow a remote user by entering their `@user@domain` handle, and the system SHALL resolve the handle, create a Follow activity, and deliver it.

#### Scenario: Follow remote user by handle
- GIVEN user `bob@local.instance`
- WHEN `bob` enters `@alice@remote.instance` in the follow input
- THEN the system performs WebFinger lookup on `remote.instance`
- AND resolves the actor URL
- AND sends a Follow activity to `alice`'s inbox
- AND creates a pending remote follow record

#### Scenario: Remote follow accepted (auto)
- GIVEN a pending remote follow request from `bob@local` to `alice@remote`
- WHEN `alice`'s server auto-accepts and sends an Accept activity to `bob`'s inbox
- THEN the system processes the Accept
- AND the follow status changes to `accepted`
- AND the remote actor's activities start appearing

#### Scenario: Remote follow rejected
- GIVEN a pending remote follow request from `bob@local` to `alice@remote`
- WHEN `alice`'s server sends a Reject activity (manual block or instance policy)
- THEN the follow request is marked as rejected
- AND no relationship is established

### Requirement: Rate limiting for outgoing deliveries
The system SHALL rate-limit outgoing deliveries to prevent hammering remote servers. The default SHALL be at most 1 request per second per remote instance.

#### Scenario: Delivery rate limited
- GIVEN multiple public bookmarks created in quick succession
- WHEN delivery to a single remote instance is queued
- THEN deliveries to that instance are spaced at least 1 second apart

### Requirement: Robust inbox spam protection
The inbox SHALL reject activities that are not properly signed, from unknown actors, or that violate activity type permissions.

#### Scenario: Unknown actor rejected
- GIVEN an unsigned POST to the shared inbox
- WHEN the activity is from an unresolvable or unknown actor
- THEN the request is rejected with 401
- AND no activity is processed