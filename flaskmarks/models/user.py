"""
User model for authentication and bookmark ownership.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from flask_login import UserMixin
from sqlalchemy import or_, desc, asc

from flaskmarks.core.extensions import db, bcrypt

if TYPE_CHECKING:
    from flask_sqlalchemy.pagination import Pagination

# Import Tag at module level for use in tags_by_click
from flaskmarks.models.tag import Tag


class User(UserMixin, db.Model):
    """
    User model representing registered users.

    Inherits from UserMixin to provide default Flask-Login implementations
    for is_authenticated, is_active, is_anonymous, and get_id.
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Unicode(255), unique=True, nullable=False)
    email = db.Column(db.Unicode(255), unique=True, nullable=False)
    password = db.Column(db.Unicode(255), nullable=False)
    last_logged = db.Column(db.DateTime)
    per_page = db.Column(db.SmallInteger, default=50)
    sort_type = db.Column(db.Unicode(255), default='clicks')
    theme = db.Column(db.Unicode(50), default='default')

    marks_rel = db.relationship('Mark', backref='owner', lazy='dynamic')

    @classmethod
    def by_uname_or_email(cls, uname: str) -> User | None:
        """
        Find a user by username or email.

        Args:
            uname: Username or email to search for

        Returns:
            User instance or None
        """
        return cls.query.filter(
            or_(User.username == uname, User.email == uname)
        ).first()

    def my_marks(self):
        """Get query for all marks owned by this user."""
        from flaskmarks.models.mark import Mark
        return Mark.query.filter(Mark.owner_id == self.id)

    def my_tags(self):
        """Get query for all tags used by this user's marks."""
        return Tag.query.filter(Tag.marks.any(owner_id=self.id))

    def all_marks(self) -> list:
        """Get all marks owned by this user."""
        return self.my_marks().all()

    def marks(self, page: int) -> Pagination:
        """
        Get paginated marks for this user.

        Args:
            page: Page number

        Returns:
            Paginated marks query result
        """
        from flaskmarks.models.mark import Mark

        base = self.my_marks()

        match self.sort_type:
            case 'clicks':
                base = base.order_by(desc(Mark.clicks)).order_by(desc(Mark.created))
            case 'dateasc':
                base = base.order_by(asc(Mark.created))
            case 'datedesc':
                base = base.order_by(desc(Mark.created))

        return base.paginate(page=page, per_page=self.per_page, error_out=False)

    def recent_marks(self, page: int, type: str) -> Pagination | bool:
        """
        Get recently added or clicked marks.

        Args:
            page: Page number
            type: Either 'added' or 'clicked'

        Returns:
            Paginated marks or False if invalid type
        """
        from flaskmarks.models.mark import Mark

        match type:
            case 'added':
                base = self.my_marks().order_by(desc(Mark.id))
                return base.paginate(page=page, per_page=self.per_page, error_out=False)
            case 'clicked':
                base = (
                    self.my_marks()
                    .filter(Mark.clicks > 0)
                    .order_by(desc(Mark.last_clicked))
                )
                return base.paginate(page=page, per_page=self.per_page, error_out=False)
            case _:
                return False

    def get_mark_by_id(self, id: int):
        """Get a specific mark by ID if owned by this user."""
        from flaskmarks.models.mark import Mark
        return self.my_marks().filter(Mark.id == id).first()

    def get_mark_type_count(self, type: str) -> int:
        """Get count of marks of a specific type."""
        from flaskmarks.models.mark import Mark
        return self.my_marks().filter(Mark.type == type).count()

    def mark_last_created(self):
        """Get the most recently created mark."""
        from flaskmarks.models.mark import Mark
        return self.my_marks().order_by(desc(Mark.created)).first()

    def q_marks_by_tag(self, tag: str, page: int) -> Pagination:
        """Get marks with a specific tag."""
        from flaskmarks.models.mark import Mark
        return (
            self.my_marks()
            .filter(Mark.tags.any(title=tag))
            .paginate(page=page, per_page=self.per_page, error_out=False)
        )

    def q_marks_by_string(self, page: int, string: str, marktype: str) -> Pagination:
        """Search marks by string in title, url, html, or description."""
        from flaskmarks.models.mark import Mark

        search_string = f"%{string}%"
        base = self.my_marks().filter(
            or_(
                Mark.title.like(search_string),
                Mark.url.like(search_string),
                Mark.full_html.like(search_string),
                Mark.description.like(search_string)
            )
        )
        return (
            base.order_by(desc(Mark.clicks))
            .paginate(page=page, per_page=self.per_page, error_out=False)
        )

    def q_marks_by_url(self, string: str):
        """Find a mark by exact URL match."""
        from flaskmarks.models.mark import Mark
        return self.my_marks().filter(Mark.url == string).first()

    def all_tags(self) -> list:
        """Get all tags used by this user's marks."""
        return self.my_tags().all()

    def tags_by_click(self, page: int) -> Pagination:
        """Get tags sorted by click count of associated marks."""
        from flaskmarks.models.mark import Mark
        return (
            self.my_tags()
            .order_by(Tag.marks.any(Mark.clicks))
            .paginate(page=page, per_page=self.per_page, error_out=False)
        )

    def authenticate_user(self, password: str) -> bool:
        """
        Verify a password against the stored hash.

        Args:
            password: Plain text password to verify

        Returns:
            True if password matches, False otherwise
        """
        return bcrypt.check_password_hash(self.password, password)

    def __repr__(self) -> str:
        return f'<User {self.username!r}>'
