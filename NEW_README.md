# Flaskmarks

A bookmark and feed management application built with Flask 3.x.

## Requirements

- Python 3.11+
- MySQL/MariaDB (or SQLite for development)

## Installation

### 1. Clone and Setup Virtual Environment

```bash
cd bookmarko
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure the Application

Edit `config.py` or set environment variables:

```bash
# Required for production
export FLASK_SECRET_KEY="your-secret-key-here"

# Database URL (default: MySQL localhost)
export DATABASE_URL="mysql://user:password@localhost/flaskmarks?charset=utf8mb4"

# For SQLite (simpler development setup)
export DATABASE_URL="sqlite:///flaskmarks.sqlite"

# Debug mode (default: enabled)
export FLASK_DEBUG=1
```

### 4. Initialize the Database

```bash
# Set Flask app
export FLASK_APP=run.py

# Initialize migrations (first time only)
flask db init

# Create migration
flask db migrate -m "Initial migration"

# Apply migrations
flask db upgrade

# Or simply create tables directly
flask create-db
```

### 5. Create a User

```bash
flask create-user
# Follow prompts for username, email, and password
```

## Running the Application

### Development Mode

```bash
# Using Flask's built-in server
flask run

# Or directly with Python
python run.py
```

The application will be available at `http://127.0.0.1:5000`

### Production Mode

```bash
# Using Gunicorn
gunicorn 'flaskmarks:create_app()' -w 4 -b 0.0.0.0:8000

# With environment variables
FLASK_DEBUG=0 FLASK_SECRET_KEY="production-secret" gunicorn 'flaskmarks:create_app()'
```

## CLI Commands

Flaskmarks provides several CLI commands for administration:

```bash
# Database management
flask create-db          # Create all database tables
flask drop-db --yes      # Drop all tables (use with caution!)

# User management
flask create-user        # Create a new user (interactive)
flask list-users         # List all registered users

# Bookmark import
flask import-marks FILE --user-id=1  # Import URLs from text file

# Database migrations (Flask-Migrate)
flask db init            # Initialize migration repository
flask db migrate -m "msg" # Create a new migration
flask db upgrade         # Apply pending migrations
flask db downgrade       # Revert last migration
```

## Features

- **Bookmarks**: Save and organize web bookmarks with automatic title and content extraction
- **Feeds**: Subscribe to RSS/Atom feeds
- **YouTube**: Save YouTube videos with metadata extraction
- **Tags**: Organize bookmarks with tags
- **Full-text Search**: Search across all bookmark content
- **Import/Export**: Import bookmarks from text files, export as JSON

## Project Structure

```
bookmarko/
├── config.py              # Application configuration
├── run.py                 # Application entry point
├── requirements.txt       # Python dependencies
├── flaskmarks/
│   ├── __init__.py       # App factory (create_app)
│   ├── cli.py            # CLI commands
│   ├── core/
│   │   ├── extensions.py # Flask extensions (db, login, etc.)
│   │   ├── blueprints.py # Blueprint registration
│   │   ├── error.py      # Error handlers
│   │   ├── filters.py    # Jinja2 template filters
│   │   └── marks_import_thread.py  # Background import
│   ├── forms/            # WTForms form classes
│   ├── models/           # SQLAlchemy models
│   ├── views/            # Blueprint views
│   ├── templates/        # Jinja2 templates
│   └── static/           # CSS, JS, images
└── migrations/           # Alembic database migrations
```

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_SECRET_KEY` | (insecure default) | Secret key for sessions |
| `DATABASE_URL` | mysql://root@localhost/flaskmarks | Database connection URL |
| `FLASK_DEBUG` | 1 | Enable debug mode |
| `SQLALCHEMY_ECHO` | false | Log SQL queries |
| `CAN_REGISTER` | True | Allow new user registration |

## Upgrading from Flask 2.x

This version has been updated to Flask 3.x with the following changes:

1. **Flask-Script replaced with Click CLI**: Use `flask <command>` instead of `python run.py <command>`
2. **Modern app factory pattern**: Application created via `create_app()` function
3. **Python 3.11+ features**: Type hints, match statements used throughout
4. **Flask-Login UserMixin**: User model now inherits from `UserMixin`
5. **Updated imports**: All Python 2-style imports replaced with Python 3 equivalents

## License

See LICENSE file for details.
