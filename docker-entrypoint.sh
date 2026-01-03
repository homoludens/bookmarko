#!/bin/bash
set -e

# Debug: show DATABASE_URL (masking password)
echo "DATABASE_URL: ${DATABASE_URL:-not set, using default}"

# Wait for database to be ready
echo "Waiting for PostgreSQL to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if python -c "
import psycopg2
import os
import sys

db_url = os.environ.get('DATABASE_URL', 'postgresql://flaskmarks:flaskmarks@db:5432/flaskmarks')
print(f'Trying to connect to: {db_url.split(\"@\")[1] if \"@\" in db_url else db_url}')

try:
    conn = psycopg2.connect(db_url)
    conn.close()
    print('Connection successful!')
    sys.exit(0)
except Exception as e:
    print(f'Connection failed: {e}')
    sys.exit(1)
"; then
        break
    fi

    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "PostgreSQL is unavailable - attempt $RETRY_COUNT/$MAX_RETRIES - sleeping"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "ERROR: Could not connect to PostgreSQL after $MAX_RETRIES attempts"
    exit 1
fi
echo "PostgreSQL is ready!"

# Run database migrations
echo "Running database migrations..."
flask db upgrade

# Check if we need to create initial user
if [ -n "$FLASKMARKS_ADMIN_USER" ] && [ -n "$FLASKMARKS_ADMIN_PASSWORD" ]; then
    echo "Checking for admin user..."
    python -c "
from flaskmarks import create_app
from flaskmarks.models.user import User
from flaskmarks.core.extensions import db, bcrypt
import os

app = create_app()
with app.app_context():
    user = User.query.filter_by(username=os.environ['FLASKMARKS_ADMIN_USER']).first()
    if not user:
        print('Creating admin user...')
        user = User(
            username=os.environ['FLASKMARKS_ADMIN_USER'],
            email=os.environ.get('FLASKMARKS_ADMIN_EMAIL', 'admin@localhost'),
        )
        user.password = bcrypt.generate_password_hash(os.environ['FLASKMARKS_ADMIN_PASSWORD']).decode('utf-8')
        print(user.password)
        db.session.add(user)
        db.session.commit()
        print('Admin user created successfully!')
    else:
        print('Admin user already exists.')
"
fi
# $2b$12$6LMd/iRf6.egXj0hGMsOqeCNEdqtikuIJm5wfuEaHnUW7I7rs5Ri2
# Generate embeddings if RAG is enabled and requested
if [ "$GENERATE_EMBEDDINGS_ON_START" = "true" ]; then
    echo "Generating embeddings for existing bookmarks..."
    flask rag generate-embeddings || echo "Warning: Embedding generation failed or RAG not configured"
fi

echo "Starting Flaskmarks..."
exec "$@"
