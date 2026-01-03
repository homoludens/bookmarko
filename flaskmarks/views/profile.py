"""
User profile and registration views.
"""
from __future__ import annotations

import io
import os
import zipfile

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import login_required

from flaskmarks.core.extensions import db, bcrypt
from flaskmarks.forms import UserRegisterForm, UserProfileForm
from flaskmarks.models import User

profile = Blueprint('profile', __name__)


def generate_bookmarklet(token: str, server_url: str) -> str:
    """Generate bookmarklet JavaScript code."""
    return f"""javascript:(function(){{
var url=encodeURIComponent(location.href);
var title=encodeURIComponent(document.title);
var xhr=new XMLHttpRequest();
xhr.open('POST','{server_url}/api/v1/quickadd',true);
xhr.setRequestHeader('Content-Type','application/json');
xhr.setRequestHeader('Authorization','Bearer {token}');
xhr.onload=function(){{
    var r=JSON.parse(xhr.responseText);
    if(r.success){{alert('Saved: '+r.data.title);}}
    else{{alert('Error: '+r.error);}}
}};
xhr.onerror=function(){{alert('Network error');}};
xhr.send(JSON.stringify({{url:decodeURIComponent(url),title:decodeURIComponent(title)}}));
}})();""".replace('\n', '').replace('    ', '')


@profile.route('/profile', methods=['GET', 'POST'])
@login_required
def userprofile():
    """Display and update user profile."""
    from flaskmarks.api.auth import generate_token, TOKEN_VALIDITY

    u = g.user
    form = UserProfileForm(obj=u)

    if form.validate_on_submit():
        form.populate_obj(u)
        if form.password.data:
            u.password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        else:
            del u.password
        db.session.add(u)
        db.session.commit()
        flash(f'User "{form.username.data}" updated.', category='success')
        return redirect(url_for('profile.userprofile'))

    # Generate API token and bookmarklet
    api_token = generate_token(u)
    server_url = request.host_url.rstrip('/')
    bookmarklet = generate_bookmarklet(api_token, server_url)

    return render_template(
        'profile/view.html',
        form=form,
        title='Profile',
        bc=g.user.get_mark_type_count('bookmark'),
        fc=g.user.get_mark_type_count('feed'),
        yc=g.user.get_mark_type_count('youtube'),
        lcm=g.user.mark_last_created(),
        api_token=api_token,
        token_validity_hours=TOKEN_VALIDITY // 3600,
        bookmarklet=bookmarklet,
        server_url=server_url
    )


@profile.route('/extension/firefox')
@login_required
def download_firefox_extension():
    """Package and serve the browser extension as XPI for Firefox."""
    # Find the browser-extension directory
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    extension_dir = os.path.join(base_dir, 'browser-extension')
    
    if not os.path.exists(extension_dir):
        abort(404, 'Browser extension not found')
    
    # Create XPI (ZIP) in memory
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(extension_dir):
            for file in files:
                if file.startswith('.') or file == 'README.md':
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, extension_dir)
                zf.write(file_path, arcname)
    
    memory_file.seek(0)
    return send_file(
        memory_file,
        mimetype='application/x-xpinstall',
        as_attachment=True,
        download_name='flaskmarks-extension.xpi'
    )


@profile.route('/register', methods=['GET', 'POST'])
def register():
    """Handle new user registration."""
    if not current_app.config.get('CAN_REGISTER', False):
        abort(403)

    form = UserRegisterForm()

    if form.validate_on_submit():
        u = User()
        form.populate_obj(u)
        u.password = bcrypt.generate_password_hash(form.password.data)
        try:
            db.session.add(u)
            db.session.commit()
            flash(
                f'New user "{form.username.data}" registered.',
                category='success'
            )
            return redirect(url_for('auth.login'))
        except Exception:
            db.session.rollback()
            flash(
                f'Problem registering "{form.username.data}".',
                category='danger'
            )

    return render_template('profile/register.html', form=form, title='Register')
