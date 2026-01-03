Flaskmarks
===============
Simple (and self educational) [Flask](http://flask.pocoo.org/) & [SQLAlchemy](http://www.sqlalchemy.org/) based bookmark and RSS feed app.

Features
========
"Flaskmarks" is a bookmark managing application. Its purpose is to be a all-in-one bookmark and RSS feed repository. Storing all bookmarks and RSS feeds in one place and make them accessible from all platforms and devices. This is by no means an original idea, but this is an interpretation of the problem.

I have added couple of features I have missed in every bookmarking app: Full Text search of bookmarked links and local copy parsed with python-readability.
This can be used as "Read latter" app.

- Bookmarking
- Full text search
- Readability



Docker Deployment (Recommended)
================================

The easiest way to run Flaskmarks is with Docker.

## Quick Start

```bash
# Clone the repository
git clone <repo-url>
cd bookmarko

# Copy and configure environment
cp .env.example .env
# Edit .env with your settings (especially POSTGRES_PASSWORD and FLASK_SECRET_KEY)

# Start the application
docker compose up -d

# View logs
docker compose logs -f app
```

The application will be available at http://localhost:5000

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Required
POSTGRES_PASSWORD=your-secure-password
FLASK_SECRET_KEY=your-secret-key  # Generate with: python -c "import secrets; print(secrets.token_hex(32))"

# Optional: Create admin user on first start
FLASKMARKS_ADMIN_USER=admin
FLASKMARKS_ADMIN_PASSWORD=your-admin-password
FLASKMARKS_ADMIN_EMAIL=admin@example.com

# Optional: RAG/AI features
RAG_ENABLED=true
GROQ_API_KEY=your-groq-api-key
```

## Development with Docker

For development with hot-reloading:

```bash
docker compose -f docker-compose.dev.yml up
```

## Docker Commands

```bash
# Build and start
docker compose up -d --build

# Stop
docker compose down

# Stop and remove volumes (deletes data!)
docker compose down -v

# View logs
docker compose logs -f

# Run Flask CLI commands
docker compose exec app flask create-user
docker compose exec app flask rag generate-embeddings

# Access PostgreSQL
docker compose exec db psql -U flaskmarks -d flaskmarks

# remove images
docker compose down -v --rmi local
docker compose up -d --build
docker volume ls

# rebuild for start

docker compose -f docker-compose.dev.yml down -v  
docker compose -f docker-compose.dev.yml up   
```

## Data Persistence

Docker volumes are used for:
- `postgres-data`: PostgreSQL database
- `embeddings-cache`: Cached embeddings
- `model-cache`: Sentence-transformer model files


Manual Installation
===================

Setting up virual envirement
============================

* `$ sudo pip install virtualenv`
* `$ virtualenv venv`
* `$ . venv/bin/activate`

Install
=======
* Create and activate a python virtualenv.
* make a copy of config.py.example to config.py and edit accordingly.
* run: `pip install -r requirements.txt`
* run: `flask --app flaskmarks db init`
* run: `flask --app flaskmarks db migrate -m "MIGRATION DESCRIPTION"`
* run: `flask --app flaskmarks db upgrade`
* run: `flask --app flaskmarks db`
* or gunicorn `gunicorn -w 4 'flaskmarks:app'`

>>> python3
>>> import nltk
>>> nltk.download('punkt')
>>> nltk.download('averaged_perceptron_tagger')
>>> nltk.download('wordnet')


Exit virtualenv
==============

$ deactivate

Ubuntu
======
Installing this app on a Ubuntu server may take a little more effort than `pip install -r requirements.txt`. On some systems the following packages need to be installed:
* run: `sudo apt-get install python-virtualenv python2.7-dev build-essential`

Upgrade
=======
* run: `python run.py db migrate`
* run: `python run.py db upgrade`

Package updates
===============
* run: `pip install --upgrade -r requirements.txt`

Simple deployment with nginx
============================
* edit and install examples/flaskmarks.nginx.example
* run: `python run.py runserver -p 5001`

Branches
========
There will at any given point be at least two branches in this repository. One
master (stable) branch, and one develop branch. The develop branch might contain
unfinished code and/or wonky solutions. I will strive to make sure that code 
merged into master is as stable as possible (given the small size of this application).

Useful Links
============
* [Flask Principal](http://pythonhosted.org/Flask-Principal/)
* [Flask SQLAlchemy](http://pythonhosted.org/Flask-SQLAlchemy/)
* [Jinja](http://jinja.pocoo.org/)
* [Filters](http://jinja.pocoo.org/docs/templates/#builtin-filters)
* [Flask and https](http://flask.pocoo.org/mailinglist/archive/2011/11/17/change-request-s-http-referer-header/#fc7dc5b7a1682ccbb4947a8013987761)
* [Flask Migrate](http://flask-migrate.readthedocs.org/en/latest/)
* [Nice Flask Tutorial](http://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world)
* [Flask online book](http://exploreflask.com/index.html)
* [Flask Blueprints](http://flask.pocoo.org/docs/blueprints/)
* [Flask-WhooshAlchemy](https://github.com/gyllstromk/Flask-WhooshAlchemy)
* [python-readability](https://github.com/buriy/python-readability)


Using
====

Import of firefox bookmark from exported json kinda works. Go to "Show all bookmarks" and than to "Backup".


Keyword extraction options
==========================

I have tried this options for keyword extraction. Newspaper3k is the current one.

* https://github.com/codelucas/newspaper - Newspaper3k: Article scraping & curation
* https://radimrehurek.com/gensim/ - Analyze plain-text documents for semantic structure
* https://github.com/csurfer/rake-nltk - Rapid Automatic Keyword Extraction algorithm


TODO
====

* try out http://getskeleton.com css instead of bootstrap, looks much simpler.



Database
========

PostgreSQL:

CREATE DATABASE bookmarko;
CREATE USER bookm_user WITH ENCRYPTED PASSWORD 'digestpass';
GRANT ALL PRIVILEGES ON DATABASE bookmarko TO bookm_user;
GRANT USAGE, CREATE ON SCHEMA public TO bookm_user;
ALTER DATABASE bookmarko OWNER TO bookm_user;

DATABASE_URL="postgresql://bookm_user:digestpass@localhost:5432/bookmarko"


## Add full text search for postgresdb 

-- Run this SQL migration
ALTER TABLE marks 
ADD COLUMN search_vector tsvector 
GENERATED ALWAYS AS (
    setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(full_html, '')), 'B')
) STORED;

-- Create index
CREATE INDEX idx_marks_search ON marks USING gin(search_vector);


#LLM 

export GROQ_API_KEY=your-api-key-here
flask rag generate-embeddings
flask rag test-query "what bookmarks do I have about python?" --user-id 1


REST API
========

Flaskmarks provides a RESTful API for programmatic access to bookmarks.

## Authentication

The API uses token-based authentication. Tokens are valid for 24 hours.

```bash
# Get a token
curl -X POST http://localhost:5000/api/v1/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'

# Response:
# {"success": true, "data": {"token": "1:1234567890:abc123...", "expires_in": 86400, "user": {...}}}
```

Use the token in subsequent requests:
```bash
curl http://localhost:5000/api/v1/marks \
  -H "Authorization: Bearer 1:1234567890:abc123..."
```

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/token` | Get auth token |
| GET | `/api/v1/auth/verify` | Verify token validity |
| POST | `/api/v1/auth/refresh` | Refresh token |

### Marks
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/marks` | List marks (paginated) |
| POST | `/api/v1/marks` | Create new mark |
| GET | `/api/v1/marks/<id>` | Get mark by ID |
| PUT | `/api/v1/marks/<id>` | Update mark |
| DELETE | `/api/v1/marks/<id>` | Delete mark |
| POST | `/api/v1/marks/<id>/click` | Increment click count |
| GET | `/api/v1/marks/search?q=<query>` | Search marks |
| GET | `/api/v1/marks/by-tag/<tag>` | Get marks by tag |
| GET | `/api/v1/marks/stats` | Get statistics |
| GET | `/api/v1/marks/export` | Export all marks |

### Tags
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/tags` | List tags with counts |
| POST | `/api/v1/tags` | Create tag |
| GET | `/api/v1/tags/<id>` | Get tag |
| PUT | `/api/v1/tags/<id>` | Rename tag |
| DELETE | `/api/v1/tags/<id>` | Remove tag from marks |
| GET | `/api/v1/tags/cloud` | Get tag cloud data |

## Examples

### Create a bookmark
```bash
curl -X POST http://localhost:5000/api/v1/marks \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "bookmark",
    "title": "Example Site",
    "url": "https://example.com",
    "description": "An example bookmark",
    "tags": ["example", "test"]
  }'
```

### Search bookmarks
```bash
curl "http://localhost:5000/api/v1/marks/search?q=python&page=1&per_page=20" \
  -H "Authorization: Bearer <token>"
```

### List marks with filtering
```bash
# Filter by type, paginate, and sort
curl "http://localhost:5000/api/v1/marks?type=bookmark&page=1&per_page=50&sort=created" \
  -H "Authorization: Bearer <token>"
```

## Response Format

All API responses follow this format:

**Success:**
```json
{
  "success": true,
  "data": { ... },
  "message": "Optional message"
}
```

**Error:**
```json
{
  "success": false,
  "error": "Error description",
  "errors": { "field": "Field-specific error" }
}
```

## Quick-Add Endpoint (Browser Extension Support)

The quick-add endpoint is designed for browser extensions and bookmarklets to save bookmarks with a single click.

### Endpoint
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/quickadd` | Quick-add a bookmark |
| GET | `/api/v1/quickadd` | Quick-add via GET (bookmarklet) |
| GET | `/api/v1/quickadd/status/<id>` | Check bookmark status |
| GET | `/api/v1/bookmarklet/script?token=<token>` | Generate bookmarklet code |

### Quick-Add Request
```bash
curl -X POST http://localhost:5000/api/v1/quickadd \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/article",
    "title": "Optional Title",
    "tags": ["optional", "tags"]
  }'
```

### Response
```json
{
  "success": true,
  "data": {
    "id": 123,
    "url": "https://example.com/article",
    "title": "Article Title",
    "status": "created",
    "metadata_extraction": "pending"
  },
  "message": "Bookmark saved"
}
```

The endpoint:
- Returns immediately with the bookmark ID
- Triggers async metadata extraction (title, description, content)
- Detects duplicates and returns existing bookmark info
- Supports JSON, form data, and query parameters

### Bookmarklet Setup

1. Get your bookmarklet code:
```bash
curl "http://localhost:5000/api/v1/bookmarklet/script?token=YOUR_TOKEN"
```

2. Create a new bookmark in your browser
3. Paste the bookmarklet code as the URL
4. Click the bookmark on any page to save it instantly


# Docker

## delete all
docker compose down --rmi local -v

## start Dev
docker compose -f docker-compose.dev.yml up --build

## logs
docker compose logs -f


## prod 
docker compose build app
