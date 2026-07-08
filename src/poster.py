"""Format jobs and post them to a Telegram channel via the Bot API."""
from __future__ import annotations

import html
import json
import logging
import time

import requests

from .models import Job
from .tagger import hashtags, is_profile_match

log = logging.getLogger(__name__)

API = "https://api.telegram.org/bot{token}/{method}"
SEND_DELAY_SECONDS = 3
MAX_MESSAGE_LEN = 4000


def format_message(job: Job) -> str:
    """Build the HTML-formatted message body for a single job."""
    lines = []
    if is_profile_match(job):
        lines.append("⭐ <b>PROFILE MATCH</b>")
    lines.append(f"☕ <b>{html.escape(job.title)}</b>")
    if job.company:
        lines.append(f"🏢 {html.escape(job.company)}")
    if job.location:
        lines.append(f"📍 {html.escape(job.location)}")
    if job.salary:
        lines.append(f"💰 {html.escape(job.salary)}")
    lines.append("")
    lines.append(f'🔗 <a href="{html.escape(job.url)}">Apply</a>')
    tags = hashtags(job)
    if tags:
        lines.append("")
        lines.append(" ".join(tags))
    text = "\n".join(lines)
    return text[:MAX_MESSAGE_LEN]


class TelegramPoster:
    def __init__(self, token: str, channel: str, all_jobs_url: str | None = None,
                 dry_run: bool = False):
        self.token = token
        self.channel = channel
        self.all_jobs_url = all_jobs_url
        self.dry_run = dry_run
        self._session = requests.Session()

    def _reply_markup(self) -> str | None:
        if not self.all_jobs_url:
            return None
        return json.dumps(
            {"inline_keyboard": [[{"text": "📋 View all jobs", "url": self.all_jobs_url}]]}
        )

    def post(self, job: Job) -> bool:
        """Send one job. Returns True on success (or in dry-run)."""
        text = format_message(job)
        if self.dry_run:
            print("-" * 50)
            print(text)
            if self.all_jobs_url:
                print(f"[button → {self.all_jobs_url}]")
            return True

        payload = {
            "chat_id": self.channel,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }
        markup = self._reply_markup()
        if markup:
            payload["reply_markup"] = markup

        url = API.format(token=self.token, method="sendMessage")
        try:
            resp = self._session.post(url, data=payload, timeout=20)
            if resp.status_code == 200 and resp.json().get("ok"):
                return True
            log.warning("Telegram send failed for %s: %s", job.title, resp.text[:200])
            return False
        except requests.RequestException as exc:
            log.warning("Telegram send error for %s: %s", job.title, exc)
            return False

    def post_batch(self, jobs: list[Job]) -> int:
        """Post jobs sequentially with a delay. Returns count sent."""
        sent = 0
        for i, job in enumerate(jobs):
            if self.post(job):
                sent += 1
            if not self.dry_run and i < len(jobs) - 1:
                time.sleep(SEND_DELAY_SECONDS)
        return sent
