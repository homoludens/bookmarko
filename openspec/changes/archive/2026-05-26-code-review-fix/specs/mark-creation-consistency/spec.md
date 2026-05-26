## ADDED Requirements

### Requirement: Mark creation uses a single persistence path
The system SHALL process mark creation requests through a single ORM object path and commit exactly once for successful requests.

#### Scenario: Valid mark with title is persisted
- **WHEN** a user submits a valid mark creation request containing a title
- **THEN** the system persists one new mark record and returns success without runtime type errors

#### Scenario: Valid mark without optional fields is persisted
- **WHEN** a user submits a valid mark creation request omitting optional fields
- **THEN** the system persists one new mark record with defaults and returns success
