"""Shared job data model used across fetchers, filter, and poster."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field


def _clean(text: str | None) -> str:
    """Collapse whitespace and strip HTML tags from a raw text field."""
    if not text:
        return ""
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
    def haystack(self) -> str:
        """Lowercased blob of all searchable text for filtering/tagging."""
        return " ".join(
            [self.title, self.company, self.location, self.description, " ".join(self.tags)]
        ).lower()
