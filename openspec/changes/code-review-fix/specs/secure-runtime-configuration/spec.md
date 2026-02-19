## ADDED Requirements

### Requirement: Production runtime requires explicit secrets
The system MUST require explicit secret configuration for production execution and SHALL fail startup when required secrets are missing.

#### Scenario: Missing secret key fails startup
- **WHEN** the app starts in production mode without a configured secret key
- **THEN** startup fails with a clear configuration error

### Requirement: Insecure production defaults are disabled
The system SHALL default production debug behavior to disabled and MUST NOT rely on hardcoded production credentials.

#### Scenario: Production debug defaults to off
- **WHEN** production runtime starts without an explicit debug override
- **THEN** debug mode is disabled

#### Scenario: Hardcoded credential fallback is not used
- **WHEN** production runtime starts without explicit database credentials
- **THEN** the process fails configuration validation instead of using hardcoded defaults
