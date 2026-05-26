## ADDED Requirements

### Requirement: Regression tests cover high-risk review paths
The system MUST include automated tests for mark creation correctness, mutation route safety, sanitized HTML rendering, and URL fetch restrictions.

#### Scenario: Mark creation regression test catches branch mismatch
- **WHEN** mark creation logic regresses to mixed object/dict access patterns
- **THEN** automated tests fail before merge

#### Scenario: CSRF/method safety regression is detected
- **WHEN** a mutation endpoint incorrectly allows GET or missing CSRF protection
- **THEN** automated tests fail before merge

#### Scenario: HTML sanitization regression is detected
- **WHEN** unsafe imported HTML can execute in rendered output
- **THEN** automated tests fail before merge

#### Scenario: SSRF guard regression is detected
- **WHEN** private-network URL fetches are inadvertently allowed
- **THEN** automated tests fail before merge
