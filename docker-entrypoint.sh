#!/bin/bash
set -e

# Wait for database to be ready
echo "Waiting for PostgreSQL to be ready..."
while ! python -c "
import psycopg2
import os
import sys
try:
    conn = psycopg2.connect(os.environ.get('DATABASE_URL', 'postgresql://localhost/flaskmarks'))
    conn.close()
    sys.exit(0)
except:
    sys.exit(1)
" 2>/dev/null; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 2
done
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
from flaskmarks.core.extensions import db
import os

app = create_app()
with app.app_context():
    user = User.query.filter_by(username=os.environ['FLASKMARKS_ADMIN_USER']).first()
    if not user:
        print('Creating admin user...')
        user = User(
            username=os.environ['FLASKMARKS_ADMIN_USER'],
            email=os.environ.get('FLASKMARKS_ADMIN_EMAIL', 'admin@localhost'),
            password=os.environ['FLASKMARKS_ADMIN_PASSWORD']
        )
        db.session.add(user)
        db.session.commit()
        print('Admin user created successfully!')
    else:
        print('Admin user already exists.')
"
fi

# Generate embeddings if RAG is enabled and requested
if [ "$GENERATE_EMBEDDINGS_ON_START" = "true" ]; then
    echo "Generating embeddings for existing bookmarks..."
    flask rag generate-embeddings || echo "Warning: Embedding generation failed or RAG not configured"
fi

echo "Starting Flaskmarks..."
exec "$@"
