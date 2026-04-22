import re
from markupsafe import escape


_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")


def _normalize_text(value, max_len=1000):
    text = '' if value is None else str(value)
    text = text.replace('\r\n', '\n').replace('\r', '\n').strip()
    text = _CONTROL_CHAR_RE.sub('', text)
    if max_len and max_len > 0:
        text = text[:max_len]
    return text


def sanitize_user_text(value, max_len=1000):
    """Normalize text input and neutralize HTML/script payloads."""
    text = _normalize_text(value, max_len=max_len)
    return str(escape(text))


def _escape_like_wildcards(value):
    return value.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')


def build_contains_pattern(value):
    cleaned = _normalize_text(value, max_len=120).lower()
    return f"%{_escape_like_wildcards(cleaned)}%"


def build_prefix_pattern(value):
    cleaned = _normalize_text(value, max_len=120).lower()
    return f"{_escape_like_wildcards(cleaned)}%"

