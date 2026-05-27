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

import requests
import time

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


# ---------------------------------------------------------------------------
# Remote actor resolution with caching
# ---------------------------------------------------------------------------

_remote_actor_cache: dict[str, tuple[dict, float]] = {}
REMOTE_ACTOR_CACHE_TTL = 3600  # 1 hour


def resolve_remote_actor(actor_url: str) -> dict | None:
    """Fetch and cache a remote actor's ActivityPub profile.

    Caches the result for 1 hour to avoid repeated HTTP requests.

    Args:
        actor_url: The remote actor's ActivityPub actor URL.

    Returns:
        Actor document dict, or None if resolution fails.
    """
    now = time.time()

    # Check cache
    if actor_url in _remote_actor_cache:
        cached_data, cached_at = _remote_actor_cache[actor_url]
        if now - cached_at < REMOTE_ACTOR_CACHE_TTL:
            return cached_data

    try:
        resp = requests.get(
            actor_url,
            headers={'Accept': 'application/activity+json'},
            timeout=15,
        )
        if resp.status_code != 200:
            return None

        data = resp.json()
        _remote_actor_cache[actor_url] = (data, now)
        return data
    except Exception:
        return None


def resolve_remote_actor_by_handle(handle: str) -> dict | None:
    """Resolve a remote actor from an @user@domain handle.

    Performs WebFinger lookup on the remote domain to find the actor URL,
    then fetches the actor profile.

    Args:
        handle: Handle in format @user@domain or user@domain.

    Returns:
        Actor document dict with inbox_url extracted, or None.
    """
    # Strip leading @ if present
    handle = handle.lstrip('@')

    if '@' not in handle:
        return None

    username, domain = handle.split('@', 1)

    try:
        # WebFinger lookup
        webfinger_url = f'https://{domain}/.well-known/webfinger?resource=acct:{username}@{domain}'
        resp = requests.get(webfinger_url, timeout=15)
        if resp.status_code != 200:
            return None

        wf_data = resp.json()

        # Find the self link (actor URL)
        actor_url = None
        for link in wf_data.get('links', []):
            if link.get('rel') == 'self':
                actor_url = link.get('href')
                break

        if not actor_url:
            return None

        # Fetch the actor profile
        actor_data = resolve_remote_actor(actor_url)
        if actor_data:
            actor_data['_inbox_url'] = actor_data.get('inbox')
            actor_data['_actor_url'] = actor_url

        return actor_data
    except Exception:
        return None


@federation.route('/user/<username>/follow-remote', methods=['POST'])
@login_required
def follow_remote(username: str):
    """Follow a remote user by @user@domain handle."""
    handle = request.form.get('handle', '').strip()
    if not handle:
        flash('Please enter a fediverse handle (e.g. @user@domain).', category='warning')
        return redirect(url_for('federation.public_profile', username=username))

    # Resolve the remote actor
    actor = resolve_remote_actor_by_handle(handle)
    if not actor:
        flash(f'Could not resolve handle: {handle}', category='danger')
        return redirect(url_for('federation.public_profile', username=username))

    inbox_url = actor.get('_inbox_url') or actor.get('inbox')
    if not inbox_url:
        flash(f'Remote actor has no inbox: {handle}', category='danger')
        return redirect(url_for('federation.public_profile', username=username))

    # Check if already following
    from flaskmarks.models import Follow
    existing = Follow.query.filter_by(
        follower_id=g.user.id,
        remote_actor_id=actor.get('_actor_url'),
    ).first()

    if existing:
        flash(f'Already following {handle}.', category='info')
        return redirect(url_for('federation.public_profile', username=username))

    # Create Follow record
    follow = Follow(
        follower_id=g.user.id,
        remote_actor_id=actor.get('_actor_url'),
        remote_inbox_url=inbox_url,
        status='accepted',
    )
    db.session.add(follow)

    # Create and queue a Follow activity
    from flaskmarks.models import Activity
    from flaskmarks.core.activitypub_delivery import enqueue_delivery

    activity = Activity(
        actor_id=g.user.id,
        activity_type='Follow',
        object_id=actor.get('_actor_url'),
        target_id=inbox_url,
    )
    db.session.add(activity)
    db.session.commit()

    # Queue delivery of the Follow activity
    enqueue_delivery(activity, inbox_url)

    flash(f'Now following {handle}!', category='success')
    return redirect(url_for('federation.public_profile', username=username))