"""
CLI commands for the Flaskmarks application.

This module replaces the deprecated Flask-Script with Click CLI commands.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from flask import Flask


def register_cli(app: Flask) -> None:
    """
    Register CLI commands with the Flask application.
    
    Args:
        app: The Flask application instance
    """
    
    @app.cli.command("create-db")
    def create_db():
        """Create all database tables."""
        from flaskmarks.core.extensions import db
        db.create_all()
        click.echo("Database tables created.")
    
    @app.cli.command("drop-db")
    @click.option("--yes", is_flag=True, help="Confirm dropping all tables")
    def drop_db(yes: bool):
        """Drop all database tables."""
        if not yes:
            click.confirm("Are you sure you want to drop all tables?", abort=True)
        from flaskmarks.core.extensions import db
        db.drop_all()
        click.echo("Database tables dropped.")
    
    @app.cli.command("create-user")
    @click.option("--username", prompt=True, help="Username for the new user")
    @click.option("--email", prompt=True, help="Email for the new user")
    @click.option("--password", prompt=True, hide_input=True, 
                  confirmation_prompt=True, help="Password for the new user")
    def create_user(username: str, email: str, password: str):
        """Create a new user."""
        from flaskmarks.core.extensions import db, bcrypt
        from flaskmarks.models import User
        
        # Check if user exists
        existing = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing:
            click.echo(f"Error: User with username '{username}' or email '{email}' already exists.")
            return
        
        user = User()
        user.username = username
        user.email = email
        user.password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        db.session.add(user)
        db.session.commit()
        click.echo(f"User '{username}' created successfully.")
    
    @app.cli.command("list-users")
    def list_users():
        """List all users."""
        from flaskmarks.models import User
        
        users = User.query.all()
        if not users:
            click.echo("No users found.")
            return
        
        click.echo(f"{'ID':<5} {'Username':<20} {'Email':<30} {'Last Login':<20}")
        click.echo("-" * 75)
        for user in users:
            last_logged = user.last_logged.strftime('%Y-%m-%d %H:%M') if user.last_logged else 'Never'
            click.echo(f"{user.id:<5} {user.username:<20} {user.email:<30} {last_logged:<20}")
    
    @app.cli.command("import-marks")
    @click.argument("filepath", type=click.Path(exists=True))
    @click.option("--user-id", type=int, required=True, help="User ID to import marks for")
    def import_marks(filepath: str, user_id: int):
        """Import bookmarks from a text file (one URL per line)."""
        from flaskmarks.models import User
        from flaskmarks.core.marks_import_thread import MarksImportThread
        
        user = User.query.get(user_id)
        if not user:
            click.echo(f"Error: User with ID {user_id} not found.")
            return
        
        with open(filepath, 'r') as f:
            urls = [line.strip() for line in f if line.strip()]
        
        click.echo(f"Importing {len(urls)} URLs for user '{user.username}'...")
        
        imported = 0
        for url in urls:
            try:
                importer = MarksImportThread(url, user_id)
                result = importer.run()
                if result:
                    imported += 1
                    click.echo(f"  Imported: {result.get('title', url)[:50]}")
            except Exception as e:
                click.echo(f"  Failed: {url} - {e}")
        
        click.echo(f"Import complete. {imported}/{len(urls)} URLs imported.")

    # RAG CLI commands
    @app.cli.group()
    def rag():
        """RAG (chat with bookmarks) management commands."""
        pass

    @rag.command("generate-embeddings")
    @click.option("--user-id", type=int, help="Generate only for specific user")
    @click.option("--force", is_flag=True, help="Regenerate all embeddings")
    @click.option("--batch-size", type=int, default=32, help="Batch size for processing")
    def generate_embeddings(user_id: int | None, force: bool, batch_size: int):
        """Generate embeddings for all bookmarks."""
        from flaskmarks.models import Mark
        from flaskmarks.core.rag.embeddings import EmbeddingService

        # Build query
        query = Mark.query
        if user_id:
            query = query.filter(Mark.owner_id == user_id)
        if not force:
            query = query.filter(Mark.embedding.is_(None))

        marks = query.all()
        total = len(marks)

        if total == 0:
            click.echo("No marks need embedding generation.")
            return

        click.echo(f"Generating embeddings for {total} marks...")

        def progress(current, total):
            pct = 100 * current // total if total else 0
            click.echo(f"  Progress: {current}/{total} ({pct}%)")

        service = EmbeddingService()
        successful, failed = service.batch_update_embeddings(
            marks,
            batch_size=batch_size,
            progress_callback=progress
        )

        click.echo(f"Complete. Successful: {successful}, Failed: {failed}")

    @rag.command("stats")
    def embedding_stats():
        """Show embedding statistics."""
        from flaskmarks.models import Mark, User

        total_marks = Mark.query.count()
        with_embeddings = Mark.query.filter(Mark.embedding.isnot(None)).count()
        without_embeddings = total_marks - with_embeddings

        click.echo("Embedding Statistics:")
        click.echo(f"  Total marks: {total_marks}")
        if total_marks > 0:
            pct = 100 * with_embeddings // total_marks
            click.echo(f"  With embeddings: {with_embeddings} ({pct}%)")
        else:
            click.echo(f"  With embeddings: {with_embeddings}")
        click.echo(f"  Without embeddings: {without_embeddings}")

        # Per-user stats
        click.echo("\nPer-user breakdown:")
        users = User.query.all()
        for user in users:
            user_total = Mark.query.filter(Mark.owner_id == user.id).count()
            user_with = Mark.query.filter(
                Mark.owner_id == user.id,
                Mark.embedding.isnot(None)
            ).count()
            click.echo(f"  {user.username}: {user_with}/{user_total}")

    @rag.command("process-pending")
    def process_pending():
        """Process pending embedding updates."""
        from flaskmarks.core.rag.tasks import (
            process_pending_embeddings,
            get_pending_updates
        )

        pending = len(get_pending_updates())
        if pending == 0:
            click.echo("No pending embedding updates.")
            return

        click.echo(f"Processing {pending} pending updates...")
        successful, failed = process_pending_embeddings(app)
        click.echo(f"Complete. Successful: {successful}, Failed: {failed}")

    @rag.command("test-query")
    @click.argument("query")
    @click.option("--user-id", type=int, required=True, help="User ID to query as")
    def test_query(query: str, user_id: int):
        """Test a RAG query from the command line."""
        from flaskmarks.core.rag.service import RAGService
        from flaskmarks.models import User

        user = User.query.get(user_id)
        if not user:
            click.echo(f"Error: User {user_id} not found.")
            return

        click.echo(f"Query: {query}")
        click.echo(f"User: {user.username}")
        click.echo("-" * 50)

        service = RAGService()
        response = service.chat(query, user_id)

        if response.error:
            click.echo(f"Error: {response.error}")
            return

        click.echo(f"Answer:\n{response.answer}")
        click.echo(f"\nSources ({len(response.sources)}):")
        for source in response.sources:
            click.echo(f"  - {source.title} (score: {source.relevance_score:.3f})")
            click.echo(f"    {source.url}")
        click.echo(f"\nTokens used: {response.tokens_used}")
