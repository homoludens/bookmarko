"""
Marks (bookmarks) views and routes.
"""
from __future__ import annotations

import concurrent.futures
import logging
import os
from collections.abc import Iterable
from datetime import datetime
from itertools import islice
from threading import Thread
from urllib.parse import urlparse

import feedparser
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    json,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required
from sqlalchemy_fulltext import FullTextSearch
import sqlalchemy_fulltext.modes as FullTextMode
from werkzeug.utils import secure_filename

from flaskmarks.core.extensions import db
from flaskmarks.core.error import is_safe_url
from flaskmarks.core.marks_import_thread import MarksImportThread
from flaskmarks.forms import (
    MarkForm,
    MarkEditForm,
    YoutubeMarkForm,
    MarksImportForm,
)
from flaskmarks.models import Mark

# Suppress SQLAlchemy fulltext cache warning
FullTextSearch.inherit_cache = False

# Module-level state for import progress tracking
_import_status: int = 0
_total_lines: int = 0

# Thread pool for background imports
_pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)

# Configure logging
logging.basicConfig(
    filename='record.log',
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s'
)

marks = Blueprint('marks', __name__)


def uri_validator(url_to_test: str) -> bool:
    """
    Validate URL format.

    Args:
        url_to_test: URL string to validate

    Returns:
        True if valid URL, False otherwise
    """
    try:
        result = urlparse(url_to_test)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


@marks.route('/')
@marks.route('/index')
def webroot():
    """Redirect to recently added marks."""
    return redirect(url_for('marks.recently_added'))


@marks.route('/marks/all')
@marks.route('/marks/all/<int:page>')
@login_required
def allmarks(page: int = 1):
    """Display all marks for current user."""
    u = g.user
    return render_template(
        'mark/index.html',
        title=f'Marks - page {page}',
        header='',
        marks=u.marks(page)
    )


@marks.route('/marks/sort/clicked')
@marks.route('/marks/sort/clicked/<int:page>')
@login_required
def recently_clicked(page: int = 1):
    """Display marks sorted by recently clicked."""
    u = g.user
    return render_template(
        'mark/index.html',
        title=f'Marks - page {page}',
        header='',
        marks=u.recent_marks(page, 'clicked')
    )


@marks.route('/marks/sort/recently')
@marks.route('/marks/sort/recently/<int:page>')
@login_required
def recently_added(page: int = 1):
    """Display marks sorted by recently added."""
    u = g.user
    return render_template(
        'mark/index.html',
        title=f'Marks - page {page}',
        header='',
        marks=u.recent_marks(page, 'added')
    )


@marks.route('/marks/search/tag/<slug>')
@marks.route('/marks/search/tag/<slug>/<int:page>')
@login_required
def mark_q_tag(slug: str, page: int = 1):
    """Search marks by tag."""
    return render_template(
        'mark/index.html',
        title=f'Marks with tag: {slug}',
        header=f'Marks with tag: {slug}',
        marks=g.user.q_marks_by_tag(slug, page)
    )


@marks.route('/marks/search/string', methods=['GET'])
@marks.route('/marks/search/string/<int:page>', methods=['GET'])
@login_required
def search_string(page: int = 1):
    """Search marks by string using fulltext search."""
    q = request.args.get('q')
    t = request.args.get('type')

    if not q and not t:
        return redirect(url_for('marks.allmarks'))

    results = (
        db.session.query(Mark)
        .filter(FullTextSearch(q, Mark, FullTextMode.NATURAL))
        .filter(Mark.owner_id == g.user.id)
        .paginate(page=page, per_page=5, error_out=False)
    )

    return render_template(
        'mark/index.html',
        title=f'Search results for: {q}',
        header=f"Search results for: '{q}'",
        marks=results
    )


@marks.route('/mark/new', methods=['GET'])
@login_required
def new_mark_selector():
    """Display new mark type selector."""
    return render_template('mark/new_selector.html', title='Select new mark type')


@marks.route('/mark/new/<string:type>', methods=['GET', 'POST'])
@login_required
def new_mark(type: str):
    """Create a new mark of specified type."""
    u = g.user

    if type not in ['bookmark', 'feed', 'youtube']:
        abort(404)

    form = YoutubeMarkForm() if type == 'youtube' else MarkForm()

    if form.validate_on_submit():
        # Check if mark with this URL exists
        if g.user.q_marks_by_url(form.url.data):
            flash(
                f'Mark with this url "{form.url.data}" already exists.',
                category='danger'
            )
            return redirect(url_for('marks.allmarks'))

        m = Mark(u.id)
        form.populate_obj(m)
        m.type = type

        # If no title, fetch content from URL
        if not form.title.data:
            r = MarksImportThread(form.url.data, u.id)
            m = r.run()

        flash(f'New {type}: "{m["title"]}", added.', category='success')
        return redirect(url_for('marks.allmarks'))

    return render_template(
        f'mark/new_{type}.html',
        title=f'New {type}',
        form=form
    )


@marks.route('/mark/view/<int:id>/<string:type>', methods=['GET'])
@login_required
def view_mark(id: int, type: str):
    """View a feed-type mark."""
    m = g.user.get_mark_by_id(id)
    if not m:
        abort(403)

    if m.type not in m.valid_feed_types:
        abort(404)

    data = feedparser.parse(m.url)

    m.clicks = m.clicks + 1
    m.last_clicked = datetime.utcnow()
    db.session.add(m)
    db.session.commit()

    return render_template(
        f'mark/view_{type}.html',
        mark=m,
        data=data,
        title=m.title,
    )


@marks.route('/mark/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_mark(id: int):
    """Edit an existing mark."""
    m = g.user.get_mark_by_id(id)
    form = MarkEditForm(obj=m)

    if not m:
        abort(403)

    if form.validate_on_submit():
        if m.url != form.url.data and g.user.q_marks_by_url(form.url.data):
            flash(
                f'Mark with this url ({form.url.data}) already exists.',
                category='danger'
            )
            return redirect(url_for('marks.allmarks'))

        form.populate_obj(m)
        m.updated = datetime.utcnow()
        db.session.add(m)
        db.session.commit()
        flash(f'Mark "{form.title.data}" updated.', category='success')

        if form.referrer.data and is_safe_url(form.referrer.data):
            return redirect(form.referrer.data)
        return redirect(url_for('marks.allmarks'))

    form.referrer.data = request.referrer
    return render_template(
        'mark/edit.html',
        mark=m,
        title=f'Edit mark - {m.title}',
        form=form
    )


@marks.route('/mark/viewhtml/<int:id>', methods=['GET', 'POST'])
@login_required
def view_html_mark(id: int):
    """View the HTML content of a mark."""
    m = g.user.get_mark_by_id(id)
    if not m:
        abort(403)
    return render_template(
        'mark/view_html.html',
        mark=m,
        title=f'View html for mark - {m.title}',
    )


@marks.route('/mark/delete/<int:id>')
@login_required
def delete_mark(id: int):
    """Delete a mark."""
    m = g.user.get_mark_by_id(id)
    if m:
        db.session.delete(m)
        db.session.commit()
        flash(f'Mark "{m.title}" deleted.', category='info')
        return redirect(url_for('marks.allmarks'))
    abort(403)


# AJAX endpoints

@marks.route('/mark/inc')
@login_required
def ajax_mark_inc():
    """Increment click count for a mark (AJAX)."""
    if request.args.get('id'):
        id = int(request.args.get('id'))
        m = g.user.get_mark_by_id(id)
        if not m:
            return jsonify(status='forbidden')
        m.clicks = m.clicks + 1
        m.last_clicked = datetime.utcnow()
        db.session.add(m)
        db.session.commit()
        return jsonify(status='success')
    return jsonify(status='error')


# Import / Export

@marks.route('/marks/export.json', methods=['GET'])
@login_required
def export_marks():
    """Export all marks as JSON."""
    u = g.user
    d = [
        {
            'title': m.title,
            'type': m.type,
            'url': m.url,
            'clicks': m.clicks,
            'last_clicked': m.last_clicked,
            'created': m.created.strftime('%s'),
            'updated': m.updated.strftime('%s') if m.updated else '',
            'tags': [t.title for t in m.tags]
        }
        for m in u.all_marks()
    ]
    return jsonify(marks=d)


def flatten(items: Iterable) -> Iterable:
    """Yield items from any nested iterable."""
    for x in items:
        if isinstance(x, Iterable) and not isinstance(x, (str, bytes)):
            yield from flatten(x)
        else:
            yield x


def iterdict2(d: dict | list) -> list[str]:
    """
    Extract all URIs from nested Firefox bookmark JSON structure.

    Args:
        d: Dictionary or list from Firefox bookmarks JSON

    Returns:
        List of bookmark URIs
    """
    final_list: list = []

    if isinstance(d, dict) and 'children' in d:
        final_list.append(iterdict2(d['children']))
    elif isinstance(d, list):
        for bookmark in d:
            if isinstance(bookmark, dict):
                if 'children' in bookmark:
                    final_list.append(iterdict2(bookmark['children']))
                if 'uri' in bookmark:
                    final_list.append(bookmark['uri'])

    return list(flatten(final_list))


def _thread_import_file(text_file_path: str, app, user_id: int) -> None:
    """
    Import bookmarks from a text file in a background thread.

    Args:
        text_file_path: Path to the text file with URLs
        app: Flask application instance
        user_id: ID of the user to import marks for
    """
    global _import_status
    maxthreads = 20
    _import_status = 0

    with open(text_file_path) as fp:
        while True:
            lines_gen = list(islice(fp, maxthreads))
            if not lines_gen:
                break

            lines_new = []
            for line in lines_gen:
                _import_status += 1
                url = line.strip()
                if url:
                    lines_new.append(url)

            with concurrent.futures.ThreadPoolExecutor(max_workers=maxthreads) as exe:
                exe.map(
                    _marks_import_thread_wrapper,
                    [(url, user_id) for url in lines_new]
                )


def _marks_import_thread_wrapper(url_user_id: tuple[str, int]) -> None:
    """Wrapper for importing a single mark in a thread."""
    url, user_id = url_user_id
    r = MarksImportThread(url, user_id)
    r.run()


@marks.route('/marks/import', methods=['GET', 'POST'])
@login_required
def import_marks():
    """Import marks from an uploaded file."""
    global _import_status, _total_lines

    current_app.logger.error('Processing default request')
    u = g.user
    form = MarksImportForm(obj=u)

    if form.validate_on_submit():
        f = form.file.data
        filename = secure_filename(f.filename)
        filepath = os.path.join(current_app.root_path, 'files', filename)

        # Ensure files directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        f.save(filepath)

        if f.content_type == 'text/plain':
            with open(filepath) as fp:
                _total_lines = sum(1 for _ in fp)

            t1 = Thread(
                target=_thread_import_file,
                args=(filepath, current_app._get_current_object(), u.id)
            )
            t1.start()

            flash(f'Import started for {_total_lines} URLs', category='success')
            return render_template(
                'profile/import_progress.html',
                total_lines=_total_lines,
                status=1
            )

    _import_status = 0
    return render_template('profile/import_progress.html', form=form, status=0)


@marks.route('/marks/import/status', methods=['GET', 'POST'])
@login_required
def get_import_status():
    """Get current import status (AJAX endpoint)."""
    return json.dumps({'status': _import_status, 'total_lines': _total_lines})


# Other routes

@marks.route('/mark/redirect/<int:id>')
@login_required
def mark_redirect(id: int):
    """Redirect through meta refresh for a mark."""
    url = url_for('marks.mark_meta', id=id)
    return render_template('meta.html', url=url)


@marks.route('/meta/<int:id>')
@login_required
def mark_meta(id: int):
    """Handle meta redirect and increment click count."""
    m = g.user.get_mark_by_id(id)
    if m:
        m.clicks = m.clicks + 1
        m.last_clicked = datetime.utcnow()
        db.session.add(m)
        return render_template('meta.html', url=m.url)
    abort(403)
