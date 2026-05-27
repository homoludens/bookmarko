"""
Entry point for running the Flaskmarks application.

Usage:
    Development: flask run
    Production: gunicorn 'flaskmarks:create_app()'
    
CLI commands:
    flask create-db     - Create database tables
    flask drop-db       - Drop database tables  
    flask create-user   - Create a new user
    flask list-users    - List all users
    flask change-password <username>  - Change a user's password
    flask import-marks  - Import bookmarks from file
    flask db init       - Initialize migrations
    flask db migrate    - Create migration
    flask db upgrade    - Apply migrations
"""
from flaskmarks import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=bool(app.config.get('DEBUG', False)))
