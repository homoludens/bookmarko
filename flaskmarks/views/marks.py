# flaskmarks/views/profile.py
import threading
from venv import logger
# from flask.globals import _request_ctx_stack
from flask import (
    Blueprint,
    render_template,
    flash,
    redirect,
    url_for,
    g,
    request,
    abort,
    jsonify,
    json,
    current_app
)
from flask_login import login_user, logout_user, login_required
from werkzeug.utils import secure_filename
import os
# from bs4 import BeautifulSoup as BSoup
from readability.readability import Document
from urllib.request import urlopen
from datetime import datetime
from urllib.parse import urlparse, urljoin
import feedparser
from typing import Iterable
from newspaper import Article, ArticleBinaryDataException
#from gensim.summarization import keywords
from werkzeug.utils import secure_filename
from bs4 import BeautifulSoup
from typing import List

from ..core.setup import app, db
from ..core.error import is_safe_url
from ..core.marks_import_thread import MarksImportThread
from ..core.theme_utils import render_themed_template

from ..forms import (
    LoginForm,
    MarkForm,
    MarkEditForm,
    YoutubeMarkForm,
    UserRegisterForm,
    UserProfileForm,
    MarksImportForm
)
from ..models import Mark
from ..models.tag import Tag

import logging
import sys
from urllib.parse import urlparse

from threading import Thread
from itertools import islice
from time import sleep
import concurrent.futures
# from flask_whooshee import Whooshee
from sqlalchemy.sql import text
from sqlalchemy import func

# from sqlalchemy_fulltext import FullText, FullTextSearch
# import sqlalchemy_fulltext.modes as FullTextMode
# Suppress warning
# https://github.com/mengzhuo/sqlalchemy-fulltext-search/issues/21
# FullTextSearch.inherit_cache = False

status = 0
total_lines = 0
import_complete = False

pool = concurrent.futures.ThreadPoolExecutor(max_workers=2)

def uri_validator(url_to_test):
    """
    Validate URL
    return true or false
    """
    try:
        result = urlparse(url_to_test)
        return all([result.scheme, result.netloc])
    except:
        return False


def extract_urls_from_bookmarks(file_path: str) -> List[str]:
    """
    Extract all URLs from a browser bookmark HTML file.

    Args:
        file_path (str): Path to the bookmark HTML file

    Returns:
        List[str]: A list of all URLs found in the bookmark file

    Example:
        >>> urls = extract_urls_from_bookmarks('bookmarks.html')
        >>> print(f"Found {len(urls)} URLs")
        >>> print(urls[:5])  # Print first 5 URLs
    """
    urls = []

    try:
        # Read the HTML file
        with open(file_path, 'r', encoding='utf-8') as file:
            html_content = file.read()

        # Parse the HTML
        soup = BeautifulSoup(html_content, 'html.parser')

        # Find all anchor tags with HREF attribute
        for link in soup.find_all('a', href=True):
            url = link['href']
            # Filter out any non-http(s) URLs (like javascript:, place:, etc.)
            if url.startswith('http://') or url.startswith('https://'):
                urls.append(url)

    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except Exception as e:
        print(f"Error processing file: {e}")

    return urls



LOG_DIR = os.environ.get('FLASKMARKS_LOG_DIR', '/app/logs')
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(LOG_DIR, 'record.log')),
    ],
    force=True,
)

marks = Blueprint('marks', __name__)


@marks.route('/')
@marks.route('/index')
def webroot():
    return redirect(url_for('marks.recently_added'))


@marks.route('/marks/all')
@marks.route('/marks/all/<int:page>')
@login_required
def allmarks(page=1):
    u = g.user
    return render_themed_template('mark/index.html',
                           title='Marks - page %d' % page,
                           header='',
                           marks=u.marks(page))


@marks.route('/marks/sort/clicked')
@marks.route('/marks/sort/clicked/<int:page>')
@login_required
def recently_clicked(page=1):
    u = g.user
    return render_themed_template('mark/index.html',
                           title='Marks - page %d' % page,
                           header='',
                           marks=u.recent_marks(page, 'clicked'))


@marks.route('/marks/sort/recently')
@marks.route('/marks/sort/recently/<int:page>')
@login_required
def recently_added(page=1):
    u = g.user
    return render_themed_template('mark/index.html',
                           title='Marks - page %d' % page,
                           header='',
                           marks=u.recent_marks(page, 'added'))


@marks.route('/marks/search/tag/<slug>')
@marks.route('/marks/search/tag/<slug>/<int:page>')
@login_required
def mark_q_tag(slug, page=1):
    return render_themed_template('mark/index.html',
                           title='Marks with tag: %s' % (slug),
                           header='Marks with tag: %s' % (slug),
                           marks=g.user.q_marks_by_tag(slug, page))


@marks.route('/marks/search/string', methods=['GET'])
@marks.route('/marks/search/string/<int:page>', methods=['GET'])
@login_required
def search_string(page=1):
    q = request.args.get('q')
    t = request.args.get('type')

    if not q and not t:
        return redirect(url_for('marks.allmarks'))

    # results = Mark.query.session.query(Mark)\
    #                     .filter(FullTextSearch(q, Mark, FullTextMode.NATURAL))\
    #                     .filter(Mark.owner_id == g.user.id)\
    #                     .paginate(page=page, per_page=5, error_out=False)

    # results = Mark.query.filter(
    #     func.to_tsvector('english', Mark.full_html).match(q))\
    #                     .filter(Mark.owner_id == g.user.id)\
    #                     .paginate(page=page, per_page=5, error_out=False)

    results = Mark.query.with_entities(Mark.id, Mark.title, Mark.url, Mark.description) \
        .filter(func.to_tsvector('english', Mark.full_html).match(q)) \
        .filter(Mark.owner_id == g.user.id) \
        .paginate(page=page, per_page=5, error_out=False)


    return render_themed_template('mark/index.html',
                           title='Search results for: %s' % (q),
                           header="Search results for: '%s'" % (q),
                           marks=results)



def search(query):
    return Mark.query.filter(
        func.to_tsvector('english', Mark.full_html).match(query)
    ).all()


@marks.route('/mark/new', methods=['GET'])
@login_required
def new_mark_selector():
    return render_themed_template('mark/new_selector.html',
                           title='Select new mark type')



@marks.route('/mark/new/<string:type>', methods=['GET', 'POST'])
@login_required
def new_mark(type):
    u = g.user

    if type not in ['bookmark', 'feed', 'youtube']:
        abort(404)

    if type == 'youtube':
        form = YoutubeMarkForm()
    else:
        form = MarkForm()
    """
    POST
    """
    if form.validate_on_submit():
        """ Check if a mark with this urs exists."""
        if g.user.q_marks_by_url(form.url.data):
            flash('Mark with this url "%s" already\
                  exists.' % (form.url.data), category='danger')
            return redirect(url_for('marks.allmarks'))
        m = Mark(u.id)
        form.populate_obj(m)
        m.type = type

        # if no title we will get title and text
        if not form.title.data:
            r = MarksImportThread(form.url.data, u.id)
            imported_mark = r.run()
            if imported_mark:
                m.title = imported_mark.get('title') or m.title
                m.description = imported_mark.get('description') or m.description
                m.full_html = imported_mark.get('full_html') or m.full_html
                if not form.tags.data and imported_mark.get('tags'):
                    tags = []
                    for tag_title in imported_mark.get('tags', []):
                        tag = Tag.check(tag_title.lower())
                        if not tag:
                            tag = Tag(tag_title.lower())
                            db.session.add(tag)
                        tags.append(tag)
                    m.tags = tags

        if not m.title:
            m.title = m.url

        db.session.add(m)
        db.session.commit()
        flash('New %s: "%s", added.' % (type, m.title), category='success')
        return redirect(url_for('marks.allmarks'))
    """
    GET
    """
    return render_themed_template('mark/new_%s.html' % (type),
                           title='New %s' % (type),
                           form=form)


@marks.route('/mark/view/<int:id>/<string:type>', methods=['GET'])
@login_required
def view_mark(id, type):
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

    return render_themed_template('mark/view_%s.html' % (type),
                           mark=m,
                           data=data,
                           title=m.title,
                           )


@marks.route('/mark/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_mark(id):
    m = g.user.get_mark_by_id(id)
    form = MarkEditForm(obj=m)
    if not m:
        abort(403)
    """
    POST
    """
    if form.validate_on_submit():
        if m.url != form.url.data and g.user.q_marks_by_url(form.url.data):
            flash('Mark with this url (%s) already\
                  exists.' % (form.url.data), category='danger')
            return redirect(url_for('marks.allmarks'))
        form.populate_obj(m)
        m.updated = datetime.utcnow()
        db.session.add(m)
        db.session.commit()
        flash('Mark "%s" updated.' % (form.title.data), category='success')
        if form.referrer.data and is_safe_url(form.referrer.data):
            return redirect(form.referrer.data)
        return redirect(url_for('marks.allmarks'))
    """
    GET
    """
    form.referrer.data = request.referrer
    return render_themed_template('mark/edit.html',
                           mark=m,
                           title='Edit mark - %s' % m.title,
                           form=form
                           )


@marks.route('/mark/viewhtml/<int:id>', methods=['GET', 'POST'])
@login_required
def view_html_mark(id):
    m = g.user.get_mark_by_id(id)
    if not m:
        abort(403)
    return render_themed_template('mark/view_html.html',
                           mark=m,
                           title='View html for mark - %s' % m.title,
                           )



@marks.route('/mark/delete/<int:id>', methods=['POST', 'DELETE'])
@login_required
def delete_mark(id):
    m = g.user.get_mark_by_id(id)
    if m:
        db.session.delete(m)
        db.session.commit()
        flash('Mark "%s" deleted.' % (m.title), category='info')
        if request.method == 'DELETE':
            return ('', 204)
        return redirect(url_for('marks.allmarks'))
    abort(403)


########
# AJAX #
########
@marks.route('/mark/inc', methods=['POST'])
@login_required
def ajax_mark_inc():
    mark_id = request.form.get('id')
    if not mark_id and request.is_json:
        payload = request.get_json(silent=True) or {}
        mark_id = payload.get('id')

    if mark_id:
        id = int(mark_id)
        m = g.user.get_mark_by_id(id)
        if not m:
            return jsonify(status='forbidden')
        m.clicks = m.clicks + 1
        m.last_clicked = datetime.utcnow()
        db.session.add(m)
        db.session.commit()
        return jsonify(status='success')
    return jsonify(status='error')


###################
# Import / Export #
###################
@marks.route('/marks/export.json', methods=['GET'])
@login_required
def export_marks():
    u = g.user
    d = [{'title': m.title,
          'type': m.type,
          'url': m.url,
          'clicks': m.clicks,
          'last_clicked': m.last_clicked,
          'created': m.created.strftime('%s'),
          'updated': m.updated.strftime('%s') if m.updated else '',
          'tags': [t.title for t in m.tags]}
         for m in u.all_marks()]
    return jsonify(marks=d)


#######################
# Import Firefox JSON #
#######################
def iterdict(d):
  app.logger.info('Info level log')
  i = 0
  if 'children' in d:
    iterdict(d['children'])
  else:
      for bookmark in d:
        if 'children' in bookmark:
            iterdict(bookmark['children'])
        if 'uri' in bookmark:
            i = i + 1
            try:
                app.logger.debug(bookmark['uri'])
                # new_imported_mark(bookmark['uri'])
            except Exception as e:
                app.logger.error(e)
                # app.logger.error('Exception %s, not added. %s' % (bookmark['uri'], e))
                # print('Exception %s, not added. %s' % (bookmark['uri'], e))


def iterdict2(d):
    """
    data = json.load(open('file.json'))
    a = iterdict2(data)
    """
    i = 0
    final_list = []
    if 'children' in d:
        l = iterdict2(d['children'])
        final_list.append(l)
    else:
        for bookmark in d:
            if 'children' in bookmark:
                l = iterdict2(bookmark['children'])
                final_list.append(l)
            if 'uri' in bookmark:
                i = i + 1
                print(i)
                try:
                    uri = bookmark['uri']
                    final_list.append(uri)
                    # print(bookmark['uri'])

                    # print(bookmark.keys())
                except Exception as e:
                    print(f"Exception: {e}")
                    uri = ''
    return list(flatten(final_list))


def flatten(items):
    """Yield items from any nested iterable; see Reference."""
    for x in items:
        if isinstance(x, Iterable) and not isinstance(x, (str, bytes)):
            for sub_x in flatten(x):
                yield sub_x
        else:
            yield x


###################
# Import mark from uri #
###################


def thread_import_file(text_file_path: str|List[str], app, user_id: int):
    maxthreads = 20
    global status
    global total_lines
    global import_complete
    
    status = 0
    import_complete = False
    lines_new = []

    if isinstance(text_file_path, str):
        # Reading from a text file with URLs
        with open(text_file_path) as fp:
            lines_new = [line.strip() for line in fp if line.strip()]
        total_lines = len(lines_new)
    elif isinstance(text_file_path, list):
        lines_new = text_file_path
        total_lines = len(lines_new)
    else:
        raise TypeError("text_file_path must be a string or a list of strings")

    if not lines_new:
        import_complete = True
        return

    with concurrent.futures.ThreadPoolExecutor(max_workers=maxthreads) as exe:
        futures = []
        for url in lines_new:
            future = exe.submit(marks_import_threads, (url, user_id))
            futures.append(future)
        
        # Wait for each future and update status
        for future in concurrent.futures.as_completed(futures):
            status += 1
            try:
                future.result()
            except Exception as e:
                print(f"Import error: {e}")
    
    import_complete = True


def marks_import_threads(url_user_id):
    url, user_id = url_user_id
    logger.info(f"importing url: {url}")
    r = MarksImportThread(url, user_id)
    r.run()


@marks.route('/marks/import', methods=['GET', 'POST'])
@login_required
def import_marks():
    global status
    global total_lines
    global import_complete

    app.logger.info('Processing default request')
    u = g.user
    form = MarksImportForm(obj=u)

    if form.validate_on_submit():
        f = form.file.data
        filename = secure_filename(f.filename)
        
        # Ensure files directory exists
        files_dir = os.path.join(app.root_path, 'files')
        os.makedirs(files_dir, exist_ok=True)
        
        file_path = os.path.join(files_dir, filename)
        f.save(file_path)

        # Reset status for new import
        status = 0
        total_lines = 0
        import_complete = False

        if f.content_type == 'text/plain':
            app.logger.info(f"content_type: {f.content_type}")
            
            # Count lines for progress
            with open(file_path) as fp:
                lines = [line.strip() for line in fp if line.strip()]
                total_lines = len(lines)

            print('Total Lines', total_lines)
            import_data = file_path  # Pass file path for text files
            
        elif f.content_type == 'text/html':
            app.logger.info(f"content_type: {f.content_type}")
            
            # Extract URLs from HTML bookmark file
            urls = extract_urls_from_bookmarks(file_path)
            total_lines = len(urls)
            print('Total URLs from HTML', total_lines)
            import_data = urls  # Pass list of URLs for HTML files
            
        else:
            flash('Unsupported file type. Please upload a .txt or .html file.', category='danger')
            return render_template('profile/import_progress.html', form=form, status=0)

        if total_lines == 0:
            flash('No URLs found in the uploaded file.', category='warning')
            return render_template('profile/import_progress.html', form=form, status=0)

        t1 = Thread(target=thread_import_file, args=(import_data, current_app._get_current_object(), u.id))
        t1.start()

        return render_template('profile/import_progress.html', total_lines=total_lines, status=1)

    status = 0
    import_complete = False
    return render_template('profile/import_progress.html', form=form, status=0)

# TODO: make this multiuser friendly
@marks.route('/marks/import/status', methods=['GET', 'POST'])
@login_required
def getStatus():
    global status
    global total_lines
    global import_complete
    statusList = {
        'status': status,
        'total_lines': total_lines,
        'complete': import_complete
    }
    return json.dumps(statusList)

#########
# Other #
#########
@marks.route('/mark/redirect/<int:id>')
@login_required
def mark_redirect(id):
    url = url_for('marks.mark_meta', id=id)
    return render_template('meta.html', url=url)


@marks.route('/meta/<int:id>')
@login_required
def mark_meta(id):
    m = g.user.get_mark_by_id(id)
    if m:
        m.clicks = m.clicks + 1
        m.last_clicked = datetime.utcnow()
        db.session.add(m)
        #db.session.commit()
        return render_template('meta.html', url=m.url)
    abort(403)
