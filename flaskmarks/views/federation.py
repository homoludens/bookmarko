"""
Federation views for same-instance follow relationships and public profiles.
"""
from __future__ import annotations

from flask import (
    Blueprint,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required

from flaskmarks.core.extensions import db
from flaskmarks.models import User, Follow

federation = Blueprint('federation', __name__)


@federation.route('/user/<username>')
def public_profile(username: str):
    """Display a public user profile page or redirect to ActivityPub actor JSON.

    Uses content negotiation based on the Accept header.
    If the client prefers application/activity+json, redirect to the actor endpoint.
    Otherwise render the HTML profile page.
    """
    user = User.query.filter_by(username=username).first()
    if not user:
        abort(404)

    # Content negotiation: if the client prefers ActivityPub JSON, redirect
    best = request.accept_mimetypes.best_match(
        ['application/activity+json', 'application/ld+json', 'text/html'],
    )
    if best in ('application/activity+json', 'application/ld+json'):
        return redirect(url_for('activitypub.actor', username=username))

    public_marks_count = user.my_marks().filter_by(visibility='public').count()

    followers_count = Follow.query.filter_by(
        followed_id=user.id,
        status='accepted',
    ).count()

    following_count = Follow.query.filter_by(
        follower_id=user.id,
        status='accepted',
    ).count()

    # Check if the current user follows this profile
    is_following = False
    if g.user and g.user.is_authenticated:
        is_following = Follow.query.filter_by(
            follower_id=g.user.id,
            followed_id=user.id,
            status='accepted',
        ).first() is not None

    return render_template(
        'federation/public_profile.html',
        profile_user=user,
        public_marks_count=public_marks_count,
        followers_count=followers_count,
        following_count=following_count,
        is_following=is_following,
        title=f'{user.username}',
    )


@federation.route('/user/<username>/follow', methods=['POST'])
@login_required
def toggle_follow(username: str):
    """Follow or unfollow a local user. Auto-accepts (no pending state)."""
    target = User.query.filter_by(username=username).first()
    if not target:
        abort(404)

    if target.id == g.user.id:
        flash('You cannot follow yourself.', category='warning')
        return redirect(url_for('federation.public_profile', username=username))

    existing = Follow.query.filter_by(
        follower_id=g.user.id,
        followed_id=target.id,
    ).first()

    if existing:
        # Unfollow: remove the relationship
        db.session.delete(existing)
        db.session.commit()
        flash(f'Unfollowed @{username}.', category='info')
    else:
        # Follow: create new accepted relationship
        follow = Follow(
            follower_id=g.user.id,
            followed_id=target.id,
            status='accepted',
        )
        db.session.add(follow)
        db.session.commit()
        flash(f'Followed @{username}.', category='success')

    return redirect(url_for('federation.public_profile', username=username))