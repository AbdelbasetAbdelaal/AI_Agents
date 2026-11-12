"""Pure helpers for the optional desktop browser."""
from urllib.parse import urlparse

ALLOWED_SCHEMES = {"http", "https"}


def normalize_browser_url(value: str) -> str:
    """Normalize a user-entered URL and reject non-web schemes."""
    value = value.strip()
    if not value:
        raise ValueError("أدخل رابط موقع أولاً.")
    candidate = value if "://" in value else "https://" + value
    parsed = urlparse(candidate)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES or not parsed.netloc:
        raise ValueError("المسموح فتح روابط المواقع التي تبدأ بـ http أو https فقط.")
    return candidate
