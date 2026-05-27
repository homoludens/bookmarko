"""Admin views for federation management."""
from __future__ import annotations

from flask import Blueprint, render_template
from flask_login import login_required

admin = Blueprint('admin', __name__, url_prefix='/admin')


@admin.route('/federation')
@login_required
def federation_status():
    """Display federation status dashboard."""
    from flaskmarks.models import Follow, DeliveryQueue, User

    total_users = User.query.count()
    users_with_actors = User.query.filter(User.actor_id.isnot(None)).count()

    accepted_follows = Follow.query.filter_by(status='accepted').count()
    remote_follows = Follow.query.filter(Follow.remote_actor_id.isnot(None)).count()
    local_follows = Follow.query.filter(Follow.followed_id.isnot(None), Follow.remote_actor_id.is_(None)).count()

    pending = DeliveryQueue.query.filter_by(status='pending').count()
    failed = DeliveryQueue.query.filter_by(status='failed').count()
    delivered = DeliveryQueue.query.filter_by(status='delivered').count()

    return render_template(
        'admin/federation_status.html',
        total_users=total_users,
        users_with_actors=users_with_actors,
        accepted_follows=accepted_follows,
        remote_follows=remote_follows,
        local_follows=local_follows,
        pending_deliveries=pending,
        failed_deliveries=failed,
        delivered_count=delivered,
    )