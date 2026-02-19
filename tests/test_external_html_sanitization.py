from flaskmarks.core.html_sanitizer import sanitize_external_html


def test_sanitize_external_html_removes_scripts_event_handlers_and_js_urls():
    html = (
        '<p onclick="alert(1)">Hello</p>'
        '<script>alert("xss")</script>'
        '<a href="javascript:alert(2)">bad</a>'
        '<img src="https://example.com/image.png" onerror="alert(3)" alt="ok">'
    )

    sanitized = sanitize_external_html(html)

    assert "<script" not in sanitized
    assert "onclick" not in sanitized
    assert "onerror" not in sanitized
    assert "javascript:" not in sanitized
    assert '<img alt="ok" src="https://example.com/image.png"/>' in sanitized


def test_sanitize_external_html_preserves_allowed_formatting_and_safe_links():
    html = '<div><h2>Title</h2><p><strong>bold</strong> and <em>emphasis</em> <a href="https://example.com">link</a></p></div>'

    sanitized = sanitize_external_html(html)

    assert "<h2>Title</h2>" in sanitized
    assert "<strong>bold</strong>" in sanitized
    assert "<em>emphasis</em>" in sanitized
    assert '<a href="https://example.com">link</a>' in sanitized


def test_sanitize_external_html_handles_empty_content():
    assert sanitize_external_html(None) == ""
    assert sanitize_external_html("") == ""
