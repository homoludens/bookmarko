"""Forms for chat functionality."""
from flask_wtf import FlaskForm
from wtforms import TextAreaField
from wtforms.validators import DataRequired, Length


class ChatForm(FlaskForm):
    """Form for chat input."""

    query = TextAreaField(
        'Question',
        validators=[
            DataRequired(message='Please enter a question'),
            Length(
                min=3,
                max=1000,
                message='Question must be between 3 and 1000 characters'
            )
        ],
        render_kw={
            'placeholder': 'Ask a question about your bookmarks...',
            'rows': 2
        }
    )
