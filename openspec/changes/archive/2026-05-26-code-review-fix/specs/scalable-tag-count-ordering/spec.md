## ADDED Requirements

### Requirement: Tag count ordering is computed in SQL before pagination
The system SHALL compute tag counts using grouped SQL aggregation and apply ordering before pagination boundaries are evaluated.

#### Scenario: Highest-count tags appear first across pages
- **WHEN** a client requests tags ordered by count
- **THEN** the returned page reflects global count ordering, not per-page post-processing order

#### Scenario: Tag listing avoids N+1 count queries
- **WHEN** a paginated tag list is requested
- **THEN** tag counts are produced without executing one additional count query per tag row
