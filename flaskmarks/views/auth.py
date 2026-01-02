"""
Authentication views for login and logout.
"""
from __future__ import annotations

from datetime import datetime

from flask import (
    Blueprint,
    flash,
    g,
    redirect,
    render_template,
    url_for,
)
from flask_login import login_required, login_user, logout_user

from flaskmarks.core.extensions import db
from flaskmarks.forms import LoginForm
from flaskmarks.models import User

auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if g.user.is_authenticated:
        return redirect(url_for('marks.allmarks'))
    
    form = LoginForm()
    
    if form.validate_on_submit():
        u = User.by_uname_or_email(form.username.data)
        if u and u.authenticate_user(form.password.data):
            u.last_logged = datetime.utcnow()
            db.session.add(u)
            db.session.commit()
            flash(f'Welcome {u.username}.', category='success')
            login_user(u, remember=form.remember_me.data)
            return redirect(url_for('marks.allmarks'))
        else:
            flash(f'Failed login for {form.username.data}.', category='danger')
            return redirect(url_for('auth.login'))
    
    return render_template('auth/login.html', title='Login', form=form)


@auth.route('/logout')
@login_required
def logout():
    """Handle user logout."""
    logout_user()
    return redirect(url_for('auth.login'))
