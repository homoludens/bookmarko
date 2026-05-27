"""Deep debug test for resolve_remote_actor."""
from __future__ import annotations


def test_debug_deep(monkeypatch):
    """Deep debug: find where resolve_remote_actor fails."""
    from flaskmarks.views.federation import resolve_remote_actor, _remote_actor_cache
    _remote_actor_cache.clear()

    call_count = 0

    def fake_get(url, **kwargs):
        nonlocal call_count
        call_count += 1
        response = type('FakeResponse', (), {
            'status_code': 200,
            'json': lambda: {'id': url, 'type': 'Person', 'preferredUsername': 'alice'},
        })()
        return response

    monkeypatch.setattr('requests.get', fake_get)

    # Manually trace the function
    import time
    actor_url = 'https://remote.instance/users/alice'
    now = time.time()
    print(f"cache check: actor_url in cache = {actor_url in _remote_actor_cache}")

    import requests
    print(f"requests.get is patched: {requests.get.__name__}")

    try:
        resp = requests.get(actor_url, headers={'Accept': 'application/activity+json'}, timeout=15)
        print(f"resp type: {type(resp)}")
        print(f"resp.status_code: {resp.status_code}")
        print(f"resp.json: {resp.json}")

        data = resp.json()
        print(f"data: {data}")

        status_check = resp.status_code != 200
        print(f"status != 200: {status_check}")
        if status_check:
            print("FAILED at status_code check")
        else:
            print("PASSED status_code check")
            _remote_actor_cache[actor_url] = (data, now)
            print("Cached OK")
            print(f"Result would be: {data}")
    except Exception as e:
        print(f"EXCEPTION: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    print(f"call_count: {call_count}")
    print(f"cache: {_remote_actor_cache}")