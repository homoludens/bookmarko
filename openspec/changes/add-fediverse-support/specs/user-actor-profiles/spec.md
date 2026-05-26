# user-actor-profiles Specification

## ADDED Requirements

### Requirement: User ActivityPub actor generation
Every registered user MUST have a corresponding ActivityPub Actor object, auto-generated on registration. The actor object SHALL conform to the ActivityPub spec with `type: Person`.

#### Scenario: New user gets actor on registration
- GIVEN a new user registration
- WHEN the user account is created
- THEN an ActivityPub Actor object is generated for that user
- AND the actor JSON-LD is served at `/api/v1/activitypub/actor/<username>`

#### Scenario: Actor contains required fields
- WHEN a remote instance fetches an actor
- THEN the response includes: `@context`, `id`, `type: "Person"`, `preferredUsername`, `name`, `inbox`, `outbox`, `followers`, `following`, `publicKey`, `url`
- AND the `id` URL is the canonical actor URL
- AND `publicKey` includes `id`, `owner`, and `publicKeyPem`

### Requirement: Actor key generation
Each user SHALL have an RSA key pair (4096-bit) generated on registration for HTTP Signatures. The private key MUST be stored encrypted in the database and never exposed via API.

#### Scenario: Keys generated on registration
- GIVEN a new user registration
- WHEN the actor is created
- THEN a 4096-bit RSA key pair is generated for that user
- AND the public key is exposed via the actor's `publicKey` field
- AND the private key is stored in the database and never returned by any API endpoint

### Requirement: WebFinger discovery
The system SHALL serve `/.well-known/webfinger` for acct URI discovery (`acct:username@domain`). It SHALL respond with the ActivityPub actor URL in the `self` link relation.

#### Scenario: WebFinger resolves local user
- GIVEN a user with username `alice` on instance `example.com`
- WHEN a query is made to `/.well-known/webfinger?resource=acct:alice@example.com`
- THEN the response includes a `self` link with `href` pointing to the user's actor URL
- AND the response has `Content-Type: application/jrd+json`

#### Scenario: WebFinger for non-existent user
- GIVEN a query for a non-existent username
- WHEN `/.well-known/webfinger?resource=acct:nonexistent@example.com`
- THEN a 404 response is returned

### Requirement: NodeInfo endpoint
The system SHALL serve `/.well-known/nodeinfo` pointing to a NodeInfo 2.0 document describing the software name, version, protocols, and usage statistics.

#### Scenario: NodeInfo discovery
- GIVEN a running instance on `example.com`
- WHEN `/.well-known/nodeinfo` is fetched
- THEN it returns links to a NodeInfo 2.0 document
- AND the NodeInfo document includes `software.name: "flaskmarks"`, protocols `["activitypub"]`, and total user count