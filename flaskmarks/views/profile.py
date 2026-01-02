"""
User profile and registration views.
"""
from __future__ import annotations

from flask import (
    Blueprint,
    abort,
    flash,
    g,
    redirect,
    render_template,
    url_for,
)
from flask_login import login_required

from flaskmarks.core.extensions import db, bcrypt
from flaskmarks.forms import UserRegisterForm, UserProfileForm
from flaskmarks.models import User

profile = Blueprint('profile', __name__)


@profile.route('/profile', methods=['GET', 'POST'])
@login_required
def userprofile():
    """Display and update user profile."""
    u = g.user
    form = UserProfileForm(obj=u)
    
    if form.validate_on_submit():
        form.populate_obj(u)
        if form.password.data:
            u.password = bcrypt.generate_password_hash(form.password.data)
        else:
            del u.password
        db.session.add(u)
        db.session.commit()
        flash(f'User "{form.username.data}" updated.', category='success')
        return redirect(url_for('profile.userprofile'))
    
    return render_template(
        'profile/view.html',
        form=form,
        title='Profile',
        bc=g.user.get_mark_type_count('bookmark'),
        fc=g.user.get_mark_type_count('feed'),
        yc=g.user.get_mark_type_count('youtube'),
        lcm=g.user.mark_last_created()
    )


@profile.route('/register', methods=['GET', 'POST'])
def register():
    """Handle new user registration."""
    from flask import current_app
    
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
