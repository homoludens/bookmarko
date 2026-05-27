# Flaskmarks Maintenance Guide

All commands assume running inside a Docker container via `docker compose exec app <command>`, or directly if running locally. For Docker, prefix each command with:

```bash
docker compose exec app <command>
```

---

## Database Migrations

Powered by **Flask-Migrate** (Alembic). Migrations run **automatically** on container startup via `docker-entrypoint.sh`.

```bash
# Apply pending migrations
flask db upgrade

# Create a new migration snapshot (after model changes)
flask db migrate -m "Description of what changed"

# Initialize migration repository (first time only)
flask db init

# Revert the last migration
flask db downgrade

# View migration history
flask db history
```

### Quick Table Reset (non-migration)

```bash
# Create all tables directly (no migration tracking)
flask create-db

# Drop all tables (destructive!)
flask drop-db --yes
```

---

## User Management

### List Users

```bash
flask list-users
```

Example output:
```
ID    Username             Email                          Last Login
---------------------------------------------------------------------------
1     admin                admin@example.com              2025-01-15 10:30
2     johndoe              john@example.com               Never
```

### Create a New User

Interactive prompts for username, email, and password:

```bash
flask create-user
```

Or non-interactively:

```bash
flask create-user --username alice --email alice@example.com --password s3cret
```

### Change a User's Password

```bash
flask change-password <username>
```

Prompts for the new password (hidden input + confirmation). Example:

```bash
flask change-password alice
New password:
Repeat for confirmation:
Password for user 'alice' changed successfully.
```

Non-interactive:

```bash
flask change-password alice --password new-s3cret
```

### Change Password via PostgreSQL Directly (fallback)

If the CLI is unavailable, generate a bcrypt hash then update manually:

```bash
# Generate hash
docker compose exec app python -c "
from flaskmarks import create_app
from flaskmarks.core.extensions import bcrypt
app = create_app()
with app.app_context():
    print(bcrypt.generate_password_hash('NEW_PASSWORD').decode('utf-8'))
"

# Apply to database
docker compose exec db psql -U flaskmarks -d flaskmarks -c "
UPDATE \"user\" SET password='THE_BCRYPT_HASH' WHERE username='target_user';
"
```

### Create Admin User on Startup

Set these environment variables in `.env` or docker compose:

```bash
FLASKMARKS_ADMIN_USER=admin
FLASKMARKS_ADMIN_PASSWORD=your-secure-password
FLASKMARKS_ADMIN_EMAIL=admin@example.com
```

The admin user is created automatically on container start if it doesn't already exist.

---

## Bookmark Import

Import URLs from a text file (one URL per line):

```bash
flask import-marks /path/to/urls.txt --user-id 1
```

---

## RAG / AI Features

### Generate Embeddings

```bash
# For all users
flask rag generate-embeddings

# For a specific user only
flask rag generate-embeddings --user-id 1

# Regenerate all (override existing)
flask rag generate-embeddings --force

# Custom batch size
flask rag generate-embeddings --batch-size 64
```

### Check Embedding Stats

```bash
flask rag stats
```

Shows total marks, marks with/without embeddings, and a per-user breakdown.

### Process Pending Updates

```bash
flask rag process-pending
```

### Test a RAG Query

```bash
flask rag test-query "what bookmarks do I have about python?" --user-id 1
```

### Auto-Generate on Startup

Set this in `.env`:

```bash
GENERATE_EMBEDDINGS_ON_START=true
```

---

## Database Access

### PostgreSQL Shell

```bash
docker compose exec db psql -U flaskmarks -d flaskmarks
```

### Common SQL Queries

```sql
-- List all users
SELECT id, username, email, last_logged FROM "user";

-- Count bookmarks per user
SELECT u.username, COUNT(m.id) as bookmark_count
FROM "user" u
LEFT JOIN marks m ON m.owner_id = u.id
GROUP BY u.id, u.username
ORDER BY bookmark_count DESC;

-- Check migration versions
SELECT * FROM alembic_version;
```

---

## Docker Lifecycle

```bash
# Build and start
docker compose up -d --build

# View logs
docker compose logs -f app

# Stop without data loss
docker compose down

# Stop and destroy data volumes
docker compose down -v

# Rebuild from scratch
docker compose down -v --rmi local
docker compose up -d --build

# Restart a service
docker compose restart app
```

---

## Production Rollout / Rollback

### Pre-deploy Checks

```bash
pytest tests/test_mark_mutation_security.py tests/test_stored_xss_regression.py tests/test_fetch_path_url_targets.py tests/test_config_and_import_status_isolation.py
```

### Verify Route Hardening

- `GET /mark/delete/<id>` should return `405`
- `GET /mark/inc` should return `405`
- UI delete/click flows should still work via form `POST` with CSRF token

### Verify Security Controls

- Stored HTML should render escaped/sanitized (no script execution)
- Private/loopback/link-local fetch targets should be rejected
- Production startup should fail fast when required secrets are missing
