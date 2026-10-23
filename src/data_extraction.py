import re
from collections.abc import Iterable
from html import unescape

TITLE_PATTERN = re.compile(
    r"<title\b[^>]*>(.*?)</title\s*>",
    re.IGNORECASE | re.DOTALL,
)

EMAIL_PATTERN = re.compile(
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    re.IGNORECASE,
)


def extract_title(html: str) -> str | None:
    """Extract and normalize the page title from HTML."""
    match = TITLE_PATTERN.search(html)

    if match is None:
        return None

    title = re.sub(r"\s+", " ", unescape(match.group(1))).strip()
    return title or None


def extract_emails(html: str) -> list[str]:
    """Extract email-like addresses from HTML."""
    return EMAIL_PATTERN.findall(html)


def transform_emails(emails: Iterable[str]) -> list[str]:
    """Normalize email addresses, remove invalid entries and duplicates."""
    normalized_emails = map(  # noqa: C417
        lambda email: email.strip().lower(),
        emails,
    )

    valid_emails = filter(
        lambda email: EMAIL_PATTERN.fullmatch(email) is not None,
        normalized_emails,
    )

    return list(dict.fromkeys(valid_emails))
