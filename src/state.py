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
EXPIRE_DAYS = 30          # a post older than this is treated as stale/closed
POST_KEEP_DAYS = 120      # forget closed posts after this long
DEFAULT_PATH = Path(__file__).resolve().parent.parent / "seen_jobs.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SeenStore:
    def __init__(self, path: Path = DEFAULT_PATH):
        self.path = path
        self._urls: dict[str, str] = {}
        self._content: dict[str, str] = {}
        self._posts: dict[str, dict] = {}
        self.load()

    def load(self) -> None:
        self._urls = {}
        self._content = {}
        self._posts = {}
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text() or "{}")
        except json.JSONDecodeError:
            return
        if isinstance(raw, dict) and "urls" in raw:
            self._urls = raw.get("urls", {})
            self._content = raw.get("content", {})
            self._posts = raw.get("posts", {})
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

    # --- posted-message tracking (for expiry) ---

    def record_post(self, job: Job, message_id: int) -> None:
        """Remember a posted job's Telegram message for later expiry."""
        self._posts[job.key] = {
            "m": message_id,
            "t": _now().isoformat(),
            "x": job.expires_at or "",
            "title": job.title,
            "company": job.company,
            "url": job.url,
            "closed": False,
        }

    def expired_open_posts(self) -> list[tuple[str, dict]]:
        """Open posts that are past their expiry date or older than EXPIRE_DAYS."""
        now = _now()
        out = []
        for key, p in self._posts.items():
            if p.get("closed"):
                continue
            expired = False
            if p.get("x"):
                try:
                    expired = datetime.fromisoformat(p["x"]) <= now
                except ValueError:
                    pass
            if not expired:
                try:
                    age = (now - datetime.fromisoformat(p["t"])).days
                    expired = age >= EXPIRE_DAYS
                except ValueError:
                    pass
            if expired:
                out.append((key, p))
        return out

    def mark_closed(self, key: str) -> None:
        if key in self._posts:
            self._posts[key]["closed"] = True
            self._posts[key]["closed_at"] = _now().isoformat()

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

    def _prune_posts(self) -> None:
        cutoff = _now().timestamp() - POST_KEEP_DAYS * 86400
        kept = {}
        for key, p in self._posts.items():
            stamp = p.get("closed_at") or p.get("t", "")
            try:
                if datetime.fromisoformat(stamp).timestamp() >= cutoff:
                    kept[key] = p
            except ValueError:
                kept[key] = p  # keep if timestamp unparseable rather than lose it
        self._posts = kept

    def prune(self) -> None:
        cutoff = _now().timestamp() - RETENTION_DAYS * 86400
        self._urls = self._prune_map(self._urls, cutoff)
        self._content = self._prune_map(self._content, cutoff)
        self._prune_posts()

    def save(self) -> None:
        self.prune()
        payload = {"urls": self._urls, "content": self._content, "posts": self._posts}
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True))
