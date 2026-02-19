## 1. Mark Creation And Mutation Safety

- [ ] 1.1 Refactor `new_mark` flow to use a single ORM object path and one commit for successful requests. `Complexity: Low`
- [x] 1.2 Add request-path tests for mark creation with title and without optional fields to prevent regression. `Complexity: Low`
- [x] 1.3 Convert state-changing mark routes from GET to POST/DELETE handlers and update route wiring. `Complexity: Middle`
- [x] 1.4 Update templates/forms for mutation endpoints to submit CSRF-protected requests. `Complexity: Low`
- [ ] 1.5 Add regression tests proving GET mutation requests are rejected and CSRF validation is enforced. `Complexity: Middle`

## 2. HTML Safety And URL Fetch Controls

- [x] 2.1 Implement HTML sanitization/escaping policy for externally sourced page content before rendering. `Complexity: High`
- [x] 2.2 Update HTML display templates to ensure unsafe markup is never executed in user context. `Complexity: Middle`
- [x] 2.3 Implement URL scheme and resolved-address validation to allow only public `http/https` targets. `Complexity: High`
- [ ] 2.4 Add fetch-path tests for blocked loopback/private/link-local targets and allowed public targets. `Complexity: Middle`
- [x] 2.5 Add security regression tests for stored XSS neutralization behavior. `Complexity: Middle`

## 3. Configuration And Import Status Isolation

- [ ] 3.1 Remove insecure production fallback secrets/credentials and enforce explicit required config. `Complexity: Low`
- [ ] 3.2 Ensure production debug defaults are disabled unless explicitly enabled in a safe context. `Complexity: Low`
- [ ] 3.3 Introduce user/job-scoped import status persistence to replace global mutable status state. `Complexity: High`
- [ ] 3.4 Update import status endpoints/handlers to require scope context and prevent cross-user leakage. `Complexity: Middle`
- [ ] 3.5 Add tests covering startup config validation failures and concurrent import status isolation. `Complexity: Middle`

## 4. Query Performance And Ordering Correctness

- [ ] 4.1 Replace tag count N+1 queries with grouped SQL aggregation query logic. `Complexity: Middle`
- [ ] 4.2 Apply count-based ordering in SQL before pagination boundaries are computed. `Complexity: Middle`
- [ ] 4.3 Validate query behavior against representative data and adjust indexes if needed. `Complexity: Middle`
- [ ] 4.4 Add tests that verify global count ordering across paginated results. `Complexity: Low`

## 5. Test Baseline And Delivery Checks

- [ ] 5.1 Create a baseline pytest structure for auth, mark CRUD, import, and security regression suites. `Complexity: Middle`
- [ ] 5.2 Add CI/local test command updates so new regression suites are executable by default. `Complexity: Low`
- [ ] 5.3 Run the new/updated test suites and fix any discovered regressions. `Complexity: High`
- [ ] 5.4 Document rollout and rollback checkpoints for route method changes and security controls. `Complexity: Low`
