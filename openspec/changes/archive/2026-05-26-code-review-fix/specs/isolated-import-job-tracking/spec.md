## ADDED Requirements

### Requirement: Import status is scoped by user or job identifier
The system SHALL store and retrieve import progress by user/job scope rather than global mutable process state.

#### Scenario: Concurrent users have isolated progress
- **WHEN** two users run imports concurrently
- **THEN** each user sees only their own import status and progress

#### Scenario: Concurrent jobs do not overwrite each other
- **WHEN** multiple import jobs are active for different scopes
- **THEN** each job status is persisted independently without cross-job overwrites

### Requirement: Import status queries return scoped data only
The system MUST require a scope key (user or job id) when returning import status.

#### Scenario: Unscoped status request is rejected
- **WHEN** a client requests import status without required scope context
- **THEN** the system returns a validation error and no global status payload
