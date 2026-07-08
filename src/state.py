"""Dedupe state: which job keys we've already seen, persisted as JSON.

The file is committed back to the repo by the GitHub Actions workflow, so it
acts as the bot's entire "database". Entries older than RETENTION_DAYS are
pruned so the file doesn't grow forever.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import Job

RETENTION_DAYS = 60
DEFAULT_PATH = Path(__file__).resolve().parent.parent / "seen_jobs.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SeenStore:
    def __init__(self, path: Path = DEFAULT_PATH):
        self.path = path
        self._urls: dict[str, str] = {}
        self._content: dict[str, str] = {}
        self.load()

    def load(self) -> None:
        self._urls = {}
        self._content = {}
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text() or "{}")
        except json.JSONDecodeError:
            return
        if isinstance(raw, dict) and "urls" in raw:
            self._urls = raw.get("urls", {})
            self._content = raw.get("content", {})
        else:
            # Migrate the old flat {url_key: ts} format.
            self._urls = raw if isinstance(raw, dict) else {}

    def has(self, job: Job) -> bool:
        return job.key in self._urls or job.content_key in self._content

    def add(self, job: Job) -> None:
        now = _now().isoformat()
        self._urls[job.key] = now
        self._content[job.content_key] = now

    def new_jobs(self, jobs: list[Job]) -> list[Job]:
        """Unseen jobs, collapsed by URL and by content within the batch too."""
        result = []
        seen_urls, seen_content = set(), set()
        for job in jobs:
            if self.has(job):
                continue
            if job.key in seen_urls or job.content_key in seen_content:
                continue
            seen_urls.add(job.key)
            seen_content.add(job.content_key)
            result.append(job)
        return result

    @staticmethod
    def _prune_map(mapping: dict, cutoff: float) -> dict:
        kept = {}
        for key, ts in mapping.items():
            try:
                if datetime.fromisoformat(ts).timestamp() >= cutoff:
                    kept[key] = ts
            except ValueError:
                continue
        return kept

    def prune(self) -> None:
        cutoff = _now().timestamp() - RETENTION_DAYS * 86400
        self._urls = self._prune_map(self._urls, cutoff)
        self._content = self._prune_map(self._content, cutoff)

    def save(self) -> None:
        self.prune()
        payload = {"urls": self._urls, "content": self._content}
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True))
