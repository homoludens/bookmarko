## Why

The current code review identifies several correctness and security defects in core bookmark flows, including issues that can cause runtime failures and exploitable behavior. These problems should be addressed now to reduce user-facing breakage and lower security risk before additional feature work.

## What Changes

- Fix the broken `new_mark` creation path so valid input does not crash and new marks are consistently persisted.
- Eliminate stored XSS risk in saved page rendering by enforcing sanitized/read-only output for scraped HTML.
- Move state-changing GET endpoints to CSRF-protected mutating routes and update templates accordingly.
- Restrict server-side URL fetching to public internet targets and block private/internal destinations to reduce SSRF exposure.
- Harden production configuration defaults by removing insecure fallbacks and requiring explicit secrets/debug settings.
- Refactor global import-status handling to avoid cross-user leakage and race conditions.
- Optimize tag counting/sorting queries to remove N+1 patterns and ensure globally correct ordering.
- Add baseline automated tests for critical auth, mark CRUD, import, and security guard paths.
- Address low-complexity correctness/maintenance items from review (click counter persistence, search/type consistency, CORS tightening).

## Capabilities

### New Capabilities
- `mark-creation-consistency`: Guarantees mark creation paths are type-safe, commit reliably, and return consistent behavior on valid input.
- `safe-scraped-html-rendering`: Ensures externally sourced HTML is sanitized or escaped before rendering to prevent stored XSS.
- `csrf-safe-mark-mutations`: Requires state-changing mark operations to use non-GET methods with CSRF protections.
- `public-only-url-fetching`: Constrains metadata/import fetches to public internet URLs and blocks private/link-local/loopback targets.
- `secure-runtime-configuration`: Defines secure defaults and required environment configuration for production deployments.
- `isolated-import-job-tracking`: Scopes import progress and status to a user/job boundary to prevent leakage and race overwrites.
- `scalable-tag-count-ordering`: Provides SQL-level aggregation and ordering for tag counts without N+1 behavior.
- `review-regression-test-baseline`: Establishes automated regression coverage for high-risk flows identified in code review.

### Modified Capabilities
- None.

## Impact

- Affected code includes `flaskmarks/views/marks.py`, `flaskmarks/core/marks_import_thread.py`, `flaskmarks/api/tags.py`, `flaskmarks/api/__init__.py`, templates under `flaskmarks/templates/**`, and environment/config entry points (`config.py`, `run.py`).
- API and route behavior changes include method updates for mutating endpoints and potentially stricter request validation.
- Dependencies may include HTML sanitization tooling and test dependencies (`pytest` plus fixtures/mocks).
- Operational impact includes safer production configuration posture and clearer constraints on outbound fetch behavior.
