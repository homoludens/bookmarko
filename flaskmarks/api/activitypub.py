"""ActivityPub federation endpoints for Flaskmarks."""
from __future__ import annotations

from flask import Blueprint, jsonify, request, abort
from flaskmarks.models import User

activitypub = Blueprint('activitypub', __name__)


def _validate_activity_body():
    """Validate that the JSON body has required 'type' and 'actor' fields.

    Returns the parsed JSON dict or aborts with 400.
    """
    if not request.is_json:
        abort(400, description='Request must be JSON')

    data = request.get_json(silent=True)
    if not data:
        abort(400, description='Invalid JSON body')

    if 'type' not in data or 'actor' not in data:
        abort(400, description='Activity must have type and actor fields')

    return data


def _dispatch_activity(data):
    """Dispatch an incoming activity to the appropriate handler.

    Returns (response_body, status_code).
    """
    activity_type = data.get('type')
    actor_url = data.get('actor')

    from flaskmarks.models import Follow, Activity as ActivityModel
    from flaskmarks.core.extensions import db

    if activity_type == 'Follow':
        # Verify the local user being followed exists
        obj = data.get('object')
        if not obj:
            return {'error': 'Follow activity must have an object'}, 400

        # The object should be an actor ID on this instance
        followed_user = User.query.filter_by(actor_id=obj).first()
        if not followed_user:
            # Try to extract username from actor_id URL
            import re
            match = re.search(r'/actor/([^/]+)', obj)
            if match:
                followed_user = User.query.filter_by(username=match.group(1)).first()

        if not followed_user or not followed_user.actor_id:
            return {'error': 'Unknown actor to follow'}, 404

        # Check if this remote actor already follows this user
        existing = Follow.query.filter_by(
            followed_id=followed_user.id,
            remote_actor_id=actor_url,
        ).first()

        if not existing:
            # Create a Follow record (follower_id is non-nullable, so we use 0 for
            # remote actors - a sentinel value that doesn't match any real user)
            follow = Follow(
                follower_id=0,  # sentinel for remote actors
                followed_id=followed_user.id,
                remote_actor_id=actor_url,
                remote_inbox_url=None,
                status='accepted',
            )
            db.session.add(follow)
            db.session.commit()

        # Auto-accept: send Accept activity back to the remote actor's inbox
        accept = {
            '@context': 'https://www.w3.org/ns/activitystreams',
            'type': 'Accept',
            'actor': followed_user.actor_id,
            'object': data,
        }

        # Queue the Accept for delivery
        try:
            from flaskmarks.core.activitypub_delivery import enqueue_delivery
            accept_activity = ActivityModel(
                actor_id=followed_user.id,
                activity_type='Accept',
                object_json=str(data),
                object_id=data.get('id'),
                target_id=actor_url,
            )
            db.session.add(accept_activity)
            db.session.commit()
            enqueue_delivery(accept_activity, None)
        except Exception:
            pass  # Queue failure shouldn't break the response

        return None, 202

    elif activity_type == 'Undo':
        obj = data.get('object')
        if not obj or not isinstance(obj, dict):
            return {'error': 'Undo activity must have an object'}, 400

        undo_type = obj.get('type')
        if undo_type == 'Follow':
            # Remove the follow relationship
            remote_actor = obj.get('actor') or actor_url
            followed_obj = obj.get('object', '')

            followed_user = User.query.filter_by(actor_id=followed_obj).first()
            if not followed_user:
                import re
                match = re.search(r'/actor/([^/]+)', followed_obj)
                if match:
                    followed_user = User.query.filter_by(username=match.group(1)).first()

            if followed_user:
                follow = Follow.query.filter_by(
                    followed_id=followed_user.id,
                    remote_actor_id=remote_actor,
                ).first()
                if follow:
                    db.session.delete(follow)
                    db.session.commit()

        return None, 202

    elif activity_type == 'Create':
        obj = data.get('object')
        if obj and isinstance(obj, dict):
            # For remote Create activities, we don't store them in our Activity
            # table since actor_id is a foreign key to local users.
            # Simply acknowledge receipt per ActivityPub spec.
            pass

        return None, 202

    elif activity_type == 'Delete':
        obj = data.get('object')
        if obj:
            # For remote Delete activities, acknowledge receipt.
            pass

        return None, 202

    else:
        # Unknown type - per ActivityPub spec, return 202 Accepted
        return None, 202


@activitypub.route('/api/v1/activitypub/inbox', methods=['POST'])
def shared_inbox():
    """Shared inbox -- accept incoming ActivityPub activities for any local actor."""
    data = _validate_activity_body()
    body, status = _dispatch_activity(data)
    if body:
        return jsonify(body), status
    return '', 202


@activitypub.route('/api/v1/activitypub/actor/<username>/inbox', methods=['POST'])
def user_inbox(username: str):
    """Per-user inbox -- delegates to the shared inbox handler."""
    user = User.query.filter_by(username=username).first()
    if not user or not user.actor_id:
        abort(404)

    data = _validate_activity_body()
    body, status = _dispatch_activity(data)
    if body:
        return jsonify(body), status
    return '', 202


@activitypub.route('/api/v1/activitypub/actor/<username>')
def actor(username: str):
    """Return ActivityPub Actor JSON-LD for a user."""
    user = User.query.filter_by(username=username).first()
    if not user or not user.actor_id:
        abort(404)

    # Build the actor document
    actor_doc = {
        '@context': [
            'https://www.w3.org/ns/activitystreams',
            'https://w3id.org/security/data/v1',
        ],
        'id': user.actor_id,
        'type': 'Person',
        'preferredUsername': user.username,
        'name': user.username,
        'inbox': user.inbox_url,
        'outbox': user.outbox_url,
        'followers': user.followers_url,
        'following': user.following_url,
        'url': user.actor_id,
        'publicKey': {
            'id': f'{user.actor_id}#main-key',
            'owner': user.actor_id,
            'publicKeyPem': user.public_key_pem,
        },
    }

    # Respond with appropriate content type for ActivityPub
    response = jsonify(actor_doc)
    # Use application/activity+json for ActivityPub clients
    # but also accept application/json
    if request.accept_mimetypes.best == 'application/activity+json' or \
       request.accept_mimetypes.best == 'application/ld+json':
        response.content_type = 'application/activity+json'
    return response


@activitypub.route('/api/v1/activitypub/actor/<username>/followers')
def actor_followers(username: str):
    """Return ActivityPub OrderedCollection of followers."""
    user = User.query.filter_by(username=username).first()
    if not user or not user.actor_id:
        abort(404)

    from flaskmarks.models import Follow

    follows = Follow.query.filter_by(
        followed_id=user.id,
        status='accepted',
    ).all()

    ordered_items = []
    for f in follows:
        follower = User.query.get(f.follower_id)
        if follower:
            ordered_items.append(follower.actor_id)

    doc = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'id': user.followers_url,
        'type': 'OrderedCollection',
        'totalItems': len(ordered_items),
        'orderedItems': ordered_items,
    }

    response = jsonify(doc)
    if request.accept_mimetypes.best == 'application/activity+json':
        response.content_type = 'application/activity+json'
    return response


@activitypub.route('/api/v1/activitypub/actor/<username>/following')
def actor_following(username: str):
    """Return ActivityPub OrderedCollection of who this user follows."""
    user = User.query.filter_by(username=username).first()
    if not user or not user.actor_id:
        abort(404)

    from flaskmarks.models import Follow

    follows = Follow.query.filter_by(
        follower_id=user.id,
        status='accepted',
    ).all()

    ordered_items = []
    for f in follows:
        followed = User.query.get(f.followed_id)
        if followed:
            ordered_items.append(followed.actor_id)

    doc = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'id': user.following_url,
        'type': 'OrderedCollection',
        'totalItems': len(ordered_items),
        'orderedItems': ordered_items,
    }

    response = jsonify(doc)
    if request.accept_mimetypes.best == 'application/activity+json':
        response.content_type = 'application/activity+json'
    return response


@activitypub.route('/api/v1/activitypub/objects/<int:mark_id>')
def bookmark_object(mark_id: int):
    """Return ActivityPub Article object for a public bookmark."""
    from flaskmarks.models import Mark

    mark = Mark.query.get(mark_id)
    if not mark or mark.visibility != 'public':
        abort(404)

    tags_list = []
    for tag in (mark.tags or []):
        tags_list.append({
            'type': 'Hashtag',
            'name': f'#{tag.title}',
        })

    base_url = request.host_url.rstrip('/')
    doc = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'id': f'{base_url}/api/v1/activitypub/objects/{mark.id}',
        'type': 'Article',
        'attributedTo': mark.owner.actor_id,
        'name': mark.title,
        'url': mark.url,
        'content': mark.description or '',
        'published': mark.created.isoformat() if mark.created else None,
        'updated': mark.updated.isoformat() if mark.updated else None,
        'tag': tags_list,
    }

    response = jsonify(doc)
    response.content_type = 'application/activity+json'
    return response


@activitypub.route('/api/v1/activitypub/actor/<username>/outbox')
def actor_outbox(username: str):
    """Return paginated OrderedCollectionPage of Create activities for public marks."""
    user = User.query.filter_by(username=username).first()
    if not user or not user.actor_id:
        abort(404)

    from flaskmarks.models import Mark

    base_url = request.host_url.rstrip('/')

    # Count public marks
    total_items = Mark.query.filter(
        Mark.owner_id == user.id,
        Mark.visibility == 'public',
    ).count()

    # Pagination
    try:
        page = int(request.args.get('page', 1))
    except (ValueError, TypeError):
        page = 1
    if page < 1:
        page = 1

    try:
        page_size = int(request.args.get('page_size', 20))
    except (ValueError, TypeError):
        page_size = 20
    if page_size < 1:
        page_size = 20
    if page_size > 100:
        page_size = 100

    offset = (page - 1) * page_size

    marks = (
        Mark.query
        .filter(Mark.owner_id == user.id, Mark.visibility == 'public')
        .order_by(Mark.created.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    ordered_items = []
    for mark in marks:
        tags_list = []
        for tag in (mark.tags or []):
            tags_list.append({
                'type': 'Hashtag',
                'name': f'#{tag.title}',
            })

        article = {
            'id': f'{base_url}/api/v1/activitypub/objects/{mark.id}',
            'type': 'Article',
            'attributedTo': user.actor_id,
            'name': mark.title,
            'url': mark.url,
            'content': mark.description or '',
            'published': mark.created.isoformat() if mark.created else None,
            'updated': mark.updated.isoformat() if mark.updated else None,
            'tag': tags_list,
        }

        create_activity = {
            'id': f'{base_url}/api/v1/activitypub/objects/{mark.id}/activity',
            'type': 'Create',
            'actor': user.actor_id,
            'object': article,
            'published': mark.created.isoformat() if mark.created else None,
        }

        ordered_items.append(create_activity)

    doc = {
        '@context': 'https://www.w3.org/ns/activitystreams',
        'id': f'{user.outbox_url}?page={page}',
        'type': 'OrderedCollectionPage',
        'partOf': user.outbox_url,
        'totalItems': total_items,
        'orderedItems': ordered_items,
    }

    response = jsonify(doc)
    response.content_type = 'application/activity+json'
    return response


@activitypub.route('/.well-known/webfinger')
def webfinger():
    """WebFinger endpoint for ActivityPub actor discovery."""
    resource = request.args.get('resource', '')

    # Parse acct:username@domain
    if not resource.startswith('acct:'):
        abort(400, description='Resource must be an acct: URI')

    acct = resource[5:]  # strip 'acct:'
    if '@' not in acct:
        abort(400, description='Invalid acct: URI format')

    username, domain = acct.split('@', 1)

    # Verify the domain matches this instance
    # request.host gives us the current domain
    if domain != request.host:
        # Try with port stripped
        host_parts = request.host.split(':')
        if domain != host_parts[0]:
            abort(404, description='User not found on this instance')

    # Find the user
    from flaskmarks.models import User
    user = User.query.filter_by(username=username).first()
    if not user or not user.actor_id:
        abort(404, description='User not found')

    # Build WebFinger response (JRD format)
    webfinger_doc = {
        'subject': resource,
        'links': [
            {
                'rel': 'self',
                'type': 'application/activity+json',
                'href': user.actor_id,
            },
        ],
    }

    return jsonify(webfinger_doc)


@activitypub.route('/.well-known/nodeinfo')
def nodeinfo_well_known():
    """NodeInfo discovery endpoint."""
    base_url = request.host_url.rstrip('/')
    return jsonify({
        'links': [
            {
                'rel': 'http://nodeinfo.diaspora.software/ns/schema/2.0',
                'href': f'{base_url}/api/v1/activitypub/nodeinfo/2.0',
            },
        ],
    })


@activitypub.route('/api/v1/activitypub/nodeinfo/2.0')
def nodeinfo():
    """NodeInfo 2.0 document."""
    from flaskmarks.models import User

    user_count = User.query.count()

    return jsonify({
        'version': '2.0',
        'software': {
            'name': 'flaskmarks',
            'version': '1.0.0',
            'repository': 'https://github.com/homoludens/bookmarko',
        },
        'protocols': [
            'activitypub',
        ],
        'services': {
            'inbound': [],
            'outbound': [],
        },
        'openRegistrations': True,
        'usage': {
            'users': {
                'total': user_count,
                'activeMonth': user_count,
                'activeHalfyear': user_count,
            },
            'localPosts': 0,
        },
        'metadata': {},
    })
