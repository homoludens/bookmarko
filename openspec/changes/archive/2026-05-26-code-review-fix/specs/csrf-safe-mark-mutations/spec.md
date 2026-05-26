## ADDED Requirements

### Requirement: Mutating mark endpoints reject GET semantics
The system SHALL expose state-changing mark operations only through mutating HTTP methods and MUST reject equivalent GET mutation requests.

#### Scenario: Delete operation via GET is rejected
- **WHEN** a client calls a mark deletion endpoint using GET
- **THEN** the system rejects the request and no mark state changes occur

#### Scenario: Delete operation via CSRF-protected form succeeds
- **WHEN** an authenticated client submits a valid CSRF-protected POST/DELETE request for mark deletion
- **THEN** the system deletes the target mark and records the change

### Requirement: Browser-initiated mutations require CSRF protection
The system MUST validate CSRF tokens for browser form-based mark mutations.

#### Scenario: Missing CSRF token fails
- **WHEN** a browser form submits a mutation request without a valid CSRF token
- **THEN** the system rejects the request and no mutation is applied
