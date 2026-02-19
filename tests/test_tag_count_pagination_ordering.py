from types import SimpleNamespace

from flaskmarks import create_app
from flaskmarks.api import auth as auth_api
from flaskmarks.api import tags as tags_api


class FakeCountColumn:
    def desc(self):
        return self


class FakeCountSubquery:
    c = SimpleNamespace(tag_id=object(), mark_count=FakeCountColumn())


class FakeCountAggregationQuery:
    def select_from(self, *_args, **_kwargs):
        return self

    def join(self, *_args, **_kwargs):
        return self

    def filter(self, *_args, **_kwargs):
        return self

    def group_by(self, *_args, **_kwargs):
        return self

    def subquery(self):
        return FakeCountSubquery()


class FakePagination:
    def __init__(self, items, page, per_page, total):
        self.items = items
        self.page = page
        self.per_page = per_page
        self.total = total
        self.pages = (total + per_page - 1) // per_page
        self.has_next = page < self.pages
        self.has_prev = page > 1


class FakeTagsQuery:
    def __init__(self, rows):
        self._rows = list(rows)
        self._ordered = False

    def join(self, *_args, **_kwargs):
        return self

    def add_columns(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        self._ordered = True
        self._rows.sort(key=lambda row: (-row[1], row[0].title))
        return self

    def paginate(self, page, per_page, error_out=False):
        assert error_out is False
        assert self._ordered, "Count ordering must happen before pagination"
        start = (page - 1) * per_page
        end = start + per_page
        return FakePagination(self._rows[start:end], page, per_page, len(self._rows))


class FakeUser:
    id = 123

    def __init__(self):
        # Intentionally unsorted by count to validate global reordering.
        self._rows = [
            (SimpleNamespace(id=1, title="alpha"), 2),
            (SimpleNamespace(id=2, title="beta"), 9),
            (SimpleNamespace(id=3, title="gamma"), 5),
            (SimpleNamespace(id=4, title="delta"), 7),
        ]

    def my_tags(self):
        return FakeTagsQuery(self._rows)


def test_list_tags_count_sort_keeps_global_order_across_pages(monkeypatch):
    app = create_app()
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    fake_user = FakeUser()
    monkeypatch.setattr(auth_api, "verify_token", lambda _token: fake_user)
    monkeypatch.setattr(
        tags_api.db.session,
        "query",
        lambda *_args, **_kwargs: FakeCountAggregationQuery(),
    )

    client = app.test_client()
    headers = {"Authorization": "Bearer valid-token"}

    page_1 = client.get("/api/v1/tags?sort=count&page=1&per_page=2", headers=headers)
    page_2 = client.get("/api/v1/tags?sort=count&page=2&per_page=2", headers=headers)

    assert page_1.status_code == 200
    assert page_2.status_code == 200

    page_1_tags = page_1.get_json()["data"]["tags"]
    page_2_tags = page_2.get_json()["data"]["tags"]

    all_counts = [tag["count"] for tag in (page_1_tags + page_2_tags)]
    all_titles = [tag["title"] for tag in (page_1_tags + page_2_tags)]

    assert all_counts == [9, 7, 5, 2]
    assert all_titles == ["beta", "delta", "gamma", "alpha"]
    assert page_1_tags[-1]["count"] >= page_2_tags[0]["count"]

