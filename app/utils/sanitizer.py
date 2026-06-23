import html

import bleach

ALLOWED_TAGS = []
ALLOWED_ATTRIBUTES = {}
ALLOWED_STYLES = []
MAX_INPUT_LENGTH = 5000


def sanitize_html(value: str) -> str:
    if not value:
        return ''
    value = str(value)
    return bleach.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,
    )


def sanitize_text(value: str, max_length: int = MAX_INPUT_LENGTH) -> str:
    if not value:
        return ''
    value = str(value).strip()
    value = sanitize_html(value)
    value = html.unescape(value)
    if max_length and len(value) > max_length:
        value = value[:max_length]
    return value


def sanitize_for_prompt(value: str) -> str:
    if not value:
        return ''
    value = sanitize_text(value, max_length=2000)
    value = value.replace('\n', ' ').replace('\r', ' ')
    return value[:500]
