import pytest

from flight_hunter.browser_utils import normalize_browser_url


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("wego.com", "https://wego.com"),
        (" https://eg.wego.com/flights ", "https://eg.wego.com/flights"),
        ("http://example.com", "http://example.com"),
    ],
)
def test_normalize_browser_url_accepts_web_urls(raw, expected):
    assert normalize_browser_url(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "javascript:alert(1)", "file:///etc/passwd", "ftp://example.com"])
def test_normalize_browser_url_rejects_non_web_urls(raw):
    with pytest.raises(ValueError):
        normalize_browser_url(raw)
