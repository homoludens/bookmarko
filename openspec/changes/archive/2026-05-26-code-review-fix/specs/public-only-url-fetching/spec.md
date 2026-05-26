## ADDED Requirements

### Requirement: URL fetches are limited to public internet targets
The system MUST allow outbound metadata/import fetches only for `http` and `https` URLs resolving to public routable destinations.

#### Scenario: Private IPv4 destination is blocked
- **WHEN** a submitted URL resolves to RFC1918/private IPv4 space
- **THEN** the system rejects the fetch before making a network request

#### Scenario: Loopback destination is blocked
- **WHEN** a submitted URL resolves to loopback or localhost
- **THEN** the system rejects the fetch before making a network request

#### Scenario: Public destination is allowed
- **WHEN** a submitted URL resolves to a public internet address over `http` or `https`
- **THEN** the system performs the fetch under normal timeout and error handling policy

### Requirement: Disallowed schemes are rejected
The system SHALL reject non-HTTP schemes for metadata/import fetching.

#### Scenario: File scheme is rejected
- **WHEN** a submitted URL uses the `file` scheme
- **THEN** the system rejects the request as invalid input
