# Pytest Regression Suite Layout

This repository keeps domain-oriented suite folders for review regressions:

- `tests/auth/`: authentication and auth-boundary regressions.
- `tests/mark_crud/`: mark creation/read/update/delete behavior.
- `tests/import_regression/`: import workflow and status isolation checks.
- `tests/security_regression/`: CSRF, XSS, SSRF, and related safety regressions.

Shared fixtures and test doubles live in `tests/conftest.py`.

Legacy root-level test modules remain supported for compatibility while suites are
incrementally organized into the domain folders.
