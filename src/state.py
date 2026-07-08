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
PAGE_WINDOW_DAYS = 14
DEFAULT_PATH = Path(__file__).resolve().parent.parent / "seen_jobs.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SeenStore:
    def __init__(self, path: Path = DEFAULT_PATH):
        self.path = path
        self._seen: dict[str, str] = {}
        self.load()

    def load(self) -> None:
        if self.path.exists():
            try:
                self._seen = json.loads(self.path.read_text() or "{}")
            except json.JSONDecodeError:
                self._seen = {}
        else:
            self._seen = {}

    def has(self, job: Job) -> bool:
        return job.key in self._seen

    def add(self, job: Job) -> None:
        self._seen[job.key] = _now().isoformat()

    def new_jobs(self, jobs: list[Job]) -> list[Job]:
        """Jobs not yet seen, de-duplicated by key within this batch too."""
        result, batch = [], set()
        for job in jobs:
            if job.key in self._seen or job.key in batch:
                continue
            batch.add(job.key)
            result.append(job)
        return result

    def prune(self) -> None:
        cutoff = _now().timestamp() - RETENTION_DAYS * 86400
        kept = {}
        for key, ts in self._seen.items():
            try:
                seen_ts = datetime.fromisoformat(ts).timestamp()
            except ValueError:
                continue
            if seen_ts >= cutoff:
                kept[key] = ts
        self._seen = kept

    def recent_keys(self, days: int = PAGE_WINDOW_DAYS) -> set[str]:
        cutoff = _now().timestamp() - days * 86400
        keys = set()
        for key, ts in self._seen.items():
            try:
                if datetime.fromisoformat(ts).timestamp() >= cutoff:
                    keys.add(key)
            except ValueError:
                continue
        return keys

    def save(self) -> None:
        self.prune()
        self.path.write_text(json.dumps(self._seen, indent=2, sort_keys=True))
