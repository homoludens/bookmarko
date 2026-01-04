"""Chat views for RAG-based bookmark interaction."""
from __future__ import annotations

from flask import (
    Blueprint,
    flash,
    g,
    jsonify,
    request,
    session,
    current_app,
)
from flask_login import login_required

from flaskmarks.core.rag.service import get_rag_service
from flaskmarks.core.theme_utils import render_themed_template
from flaskmarks.forms.chat import ChatForm

chat = Blueprint('chat', __name__)


@chat.route('/chat', methods=['GET'])
@login_required
def chat_page():
    """Render the chat interface."""
    form = ChatForm()

    # Get chat history from session
    chat_history = session.get('chat_history', [])

    return render_themed_template(
        'chat/index.html',
        title='Chat with Bookmarks',
        form=form,
        chat_history=chat_history
    )


@chat.route('/chat/send', methods=['POST'])
@login_required
def send_message():
    """Handle chat message submission."""
    form = ChatForm()

    if not form.validate_on_submit():
        return jsonify({
            'error': 'Invalid form submission',
            'errors': form.errors
        }), 400

    query = form.query.data.strip()
    if not query:
        return jsonify({'error': 'Please enter a question'}), 400

    # Get chat history from session
    chat_history = session.get('chat_history', [])

    # Get RAG response
    rag_service = get_rag_service()
    response = rag_service.chat(
        query=query,
        user_id=g.user.id,
        chat_history=chat_history
    )

    if response.error:
        return jsonify({'error': response.error}), 500

    # Update chat history in session
    chat_history.append({'role': 'user', 'content': query})
    chat_history.append({'role': 'assistant', 'content': response.answer})

    # Limit history size
    max_history = current_app.config.get('CHAT_MAX_HISTORY', 10) * 2
    session['chat_history'] = chat_history[-max_history:]

    return jsonify({
        'answer': response.answer,
        'sources': [
            {
                'id': s.mark_id,
                'title': s.title,
                'url': s.url,
                'score': round(s.relevance_score, 3)
            }
            for s in response.sources
        ],
        'tokens_used': response.tokens_used
    })


@chat.route('/chat/clear', methods=['POST'])
@login_required
def clear_history():
    """Clear chat history."""
    session.pop('chat_history', None)
    flash('Chat history cleared.', category='info')
    return jsonify({'status': 'ok'})


@chat.route('/chat/history', methods=['GET'])
@login_required
def get_history():
    """Get current chat history."""
    chat_history = session.get('chat_history', [])
    return jsonify({'history': chat_history})
