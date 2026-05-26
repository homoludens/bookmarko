## Context

The proposal targets a cross-cutting remediation effort across Flask views, API routes, templates, import/fetch services, and runtime configuration. Current issues include correctness failures (`new_mark`), exploitable stored XSS and CSRF patterns, SSRF exposure in server-side URL fetching, weak production defaults, and scalability/reliability problems (global import status and tag N+1 queries). The codebase is a Flask app with SQLAlchemy and mixed web/API surfaces, so design decisions must preserve behavior while tightening security and data integrity.

## Goals / Non-Goals

**Goals:**
- Eliminate high-risk correctness and security defects from code review findings.
- Introduce a consistent pattern for safe mutation routes, safe HTML rendering, and constrained outbound fetching.
- Improve data/query reliability for import status and tag count ordering.
- Establish regression tests for the identified high-risk paths.
- Keep rollout incremental and reversible where possible.

**Non-Goals:**
- Large feature additions unrelated to review findings.
- Full architecture rewrite of the marks module in this change.
- Perfect analytics-grade click counting; best-effort semantics remain acceptable.

## Decisions

1. Normalize mark creation to a single ORM path.
- Decision: Refactor `new_mark` so all branches construct/update a `Mark` object and commit once.
- Rationale: Removes type/branch inconsistencies and guarantees persistence for valid paths.
- Alternative considered: Patch only failing branches; rejected because branch drift would remain likely.

2. Enforce sanitized/read-only rendering for scraped HTML.
- Decision: Sanitize on ingestion and treat rendering as untrusted by default (no raw trusted HTML execution).
- Rationale: Defense at ingest plus safer template rendering closes stored XSS vector.
- Alternative considered: CSP-only mitigation; rejected because CSP is defense-in-depth, not sufficient as primary control.

3. Require mutating endpoints to use CSRF-protected non-GET methods.
- Decision: Convert mark-delete/increment style mutations to POST/DELETE handlers, with CSRF tokens in form-based flows.
- Rationale: Aligns with HTTP semantics and blocks link/image-trigger CSRF.
- Alternative considered: Keep GET and add referrer checks; rejected as weaker and easier to bypass.

4. Restrict SSRF by network-aware URL validation.
- Decision: Allowlist `http/https`, resolve hostnames, block loopback/link-local/private ranges, and reject internal targets before fetch.
- Rationale: Prevents internal network probing while preserving public URL fetch functionality.
- Alternative considered: Domain blocklist only; rejected as incomplete against direct IP/DNS-rebinding style abuse.

5. Harden production configuration defaults.
- Decision: Remove insecure credential/secret fallbacks, default debug off in production paths, and fail fast when required secrets are missing.
- Rationale: Secure-by-default startup behavior reduces accidental exposure.
- Alternative considered: Keep dev-friendly fallbacks globally; rejected due to production risk.

6. Replace global import status state with user/job-scoped tracking.
- Decision: Track import progress by persisted job identity (user/job id), not process-global mutable variables.
- Rationale: Prevents cross-user leakage and race overwrites.
- Alternative considered: In-memory per-process map; rejected because it remains fragile under multi-worker deployment.

7. Move tag count ordering into SQL aggregation.
- Decision: Implement grouped count query with ordering before pagination.
- Rationale: Eliminates N+1 and restores globally correct ordering.
- Alternative considered: Post-pagination sort in Python; rejected because ordering remains incorrect across pages.

8. Add focused regression tests first, then expand coverage.
- Decision: Add pytest coverage for auth-protected mutations, mark creation correctness, import URL constraints, and XSS/CSRF guard behavior.
- Rationale: Catches regressions in highest-risk areas without requiring immediate full-suite buildout.
- Alternative considered: Delay tests until all fixes land; rejected due to high regression risk.

## Risks / Trade-offs

- [Route method changes may break existing clients/bookmarks] -> Mitigation: keep compatibility redirects where possible, document method changes, and update templates/callers in same change.
- [Sanitization may strip desired formatting from saved pages] -> Mitigation: adopt conservative allowlist and validate against representative captured content.
- [DNS/IP validation can produce false positives/operational edge cases] -> Mitigation: explicit error messages, structured logging, and test fixtures for allowed/blocked URL classes.
- [Import job persistence adds schema/operational complexity] -> Mitigation: minimal job model with clear lifecycle and cleanup strategy.
- [Query rewrite may affect performance on large datasets unexpectedly] -> Mitigation: inspect generated SQL, add indexes if needed, and verify with realistic sample data.

## Migration Plan

1. Ship route/template updates for mutating operations and verify CSRF-protected flows.
2. Deploy mark-creation bug fix and sanitized rendering changes.
3. Roll out SSRF protections and monitor rejected URL logs for unexpected breakage.
4. Introduce scoped import-job tracking and remove global status usage.
5. Release tag aggregation query changes and validate pagination ordering.
6. Enforce secure runtime config defaults in deployment config.
7. Run/enable regression test set in CI and block merges on failures.

Rollback strategy:
- Revert individual commits by concern area (routes, sanitization, SSRF, import tracking, queries, config) if breakage is detected.
- Keep data migrations additive when possible; avoid destructive schema operations in this change.

## Open Questions

- Should sanitized HTML be stored as replacement for raw content, or should raw be retained separately for future re-processing?
- Do any non-browser clients rely on current GET mutation endpoints and require temporary compatibility handling?
- What is the preferred persistence model for import jobs in this repo (new table vs reuse existing metadata structures)?
- Are there environment-specific allowed outbound domains needed beyond generic public-internet policy?
