"""Shared job data model used across fetchers, filter, and poster."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field


_REMOTE_LOC = re.compile(
    r"\b(remote|world\s?wide|anywhere|distributed|work from home|wfh|"
    r"home[\s-]?office)\b",
    re.I,
)


def _fix_mojibake(text: str) -> str:
    """Repair UTF-8 that was double-encoded upstream (e.g. "SÃªnior" → "Sênior").

    Only attempted when the classic mojibake markers are present, so correctly
    encoded text is left untouched.
    """
    if "Ã" not in text and "Â" not in text:
        return text
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def _clean(text: str | None) -> str:
    """Collapse whitespace, strip HTML tags, and repair mojibake."""
    if not text:
        return ""
    text = _fix_mojibake(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


@dataclass
class Job:
    """A normalized job posting from any source."""

    title: str
    company: str
    url: str
    source: str
    location: str = ""
    salary: str = ""
    tags: list[str] = field(default_factory=list)
    description: str = ""
    published_at: str = ""
    expires_at: str = ""  # ISO date when the posting closes, if the source says

    def __post_init__(self) -> None:
        self.title = _clean(self.title)
        self.company = _clean(self.company)
        self.location = _clean(self.location)
        self.salary = _clean(self.salary)
        self.description = _clean(self.description)
        self.tags = [_clean(t).lower() for t in self.tags if _clean(t)]

    @property
    def key(self) -> str:
        """Stable dedupe key derived from the normalized apply URL."""
        normalized = self.url.split("?")[0].rstrip("/").lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]

    @property
    def content_key(self) -> str:
        """Cross-source dedupe key: same company + title on another board.

        Normalizes away punctuation, seniority abbreviations, and gender tags
        so the same role posted to LinkedIn, Indeed and a company site collapses
        to one entry regardless of which URL it came from.
        """
        # Drop location/qualifier decorations some boards append to titles,
        # e.g. "Staff Backend Engineer - Alerting | Germany | Remote", so the
        # same role in 5 countries collapses to one key.
        title = self.title.split("|")[0]
        title = re.sub(r"\(.*?\)", " ", title)  # strip parentheticals
        text = f"{self.company} {title}".lower()
        text = re.sub(r"\bm/w/d\b|\bf/m/d\b", " ", text)
        text = re.sub(r"\bsr\b", "senior", text)
        text = re.sub(r"\bjr\b", "junior", text)
        text = re.sub(r"[^a-z0-9]", "", text)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    @property
    def is_remote(self) -> bool:
        """Remote status judged from location + tags (not free-text description)."""
        where = f"{self.location} {' '.join(self.tags)}"
        return bool(_REMOTE_LOC.search(where))

    @property
    def haystack(self) -> str:
        """Lowercased blob of all searchable text for filtering/tagging."""
        return " ".join(
            [self.title, self.company, self.location, self.description, " ".join(self.tags)]
        ).lower()
