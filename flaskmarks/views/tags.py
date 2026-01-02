"""
Tag browsing views.
"""
from __future__ import annotations

from flask import Blueprint, g, render_template
from flask_login import login_required

tags = Blueprint('tags', __name__)


@tags.route('/tags/cloud', methods=['GET'])
@login_required
def cloud():
    """Display tag cloud."""
    return render_template(
        'tag/cloud.html',
        title='Tag cloud',
        header='',
        tags=g.user.all_tags()
    )


@tags.route('/tags/sort/clicks', methods=['GET'])
@tags.route('/tags/sort/clicks/<int:page>')
@login_required
def by_clicks(page: int = 1):
    """Display tags sorted by click count."""
    u = g.user
    return render_template(
        'tag/index.html',
        title=f'Tags - page {page}',
        header='',
        tags=u.tags_by_click(page)
    )
