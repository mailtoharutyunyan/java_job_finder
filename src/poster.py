"""Format jobs and post them to a Telegram channel via the Bot API."""
from __future__ import annotations

import html
import json
import logging
import re
import time

import requests

from .models import Job
from .tagger import go_fit, hashtags, is_profile_match, java_fit, source_hashtag

log = logging.getLogger(__name__)

API = "https://api.telegram.org/bot{token}/{method}"
SEND_DELAY_SECONDS = 3
MAX_MESSAGE_LEN = 4000
DRY_RUN_MSG_ID = -1  # sentinel returned by post() in dry-run (no real message)
SNIPPET_LEN = 240

# Hashtag → display name for the "stack" line (skills only, not meta tags).
_STACK_DISPLAY = {
    "#java": "Java", "#spring": "Spring", "#fullstack": "Full-stack",
    "#angular": "Angular", "#react": "React", "#ai": "AI/ML", "#aws": "AWS",
    "#gcp": "GCP", "#azure": "Azure", "#kubernetes": "Kubernetes",
    "#docker": "Docker", "#kafka": "Kafka", "#microservices": "Microservices",
    "#kotlin": "Kotlin", "#golang": "Go",
}

_SOURCE_DISPLAY = {
    "remotive": "Remotive", "arbeitnow": "Arbeitnow", "jobicy": "Jobicy",
    "remoteok": "RemoteOK", "himalayas": "Himalayas",
    "weworkremotely": "WeWorkRemotely", "workingnomads": "Working Nomads",
    "themuse": "The Muse", "landingjobs": "Landing.jobs", "nodesk": "NoDesk",
    "remoteyeah": "RemoteYeah", "tryremotely": "TryRemotely",
    "remotefirstjobs": "RemoteFirstJobs", "euremotejobs": "EU Remote Jobs",
    "jobspresso": "Jobspresso", "jobscollider": "JobsCollider",
    "golangprojects": "Golangprojects",
    "linkedin": "LinkedIn", "indeed": "Indeed", "glassdoor": "Glassdoor",
}


def _seniority(job: Job) -> str:
    t = job.haystack
    if re.search(r"\b(principal|staff|lead|head of)\b", t):
        return "Lead / Principal"
    if re.search(r"\b(senior|sr\.?)\b", t):
        return "Senior"
    if re.search(r"\b(junior|jr\.?|entry[\s-]?level|graduate|intern)\b", t):
        return "Junior"
    if re.search(r"\b(mid|middle|intermediate)\b", t):
        return "Mid"
    return ""


def _employment_type(job: Job) -> str:
    t = job.haystack
    if re.search(r"\b(full[\s-]?time|fulltime)\b", t):
        return "Full-time"
    if re.search(r"\b(part[\s-]?time)\b", t):
        return "Part-time"
    if re.search(r"\b(contract|freelance|b2b)\b", t):
        return "Contract"
    if re.search(r"\b(intern(ship)?)\b", t):
        return "Internship"
    return ""


def _location_line(job: Job) -> str:
    loc = job.location or "Remote"
    icon = "🌍" if re.search(r"world|anywhere|global", loc, re.I) else "📍"
    return f"{icon} {html.escape(loc)}"


def _source_name(job: Job) -> str:
    src = job.source.lower()
    if src.startswith("greenhouse"):
        return "Greenhouse"
    if src.startswith("lever"):
        return "Lever"
    key = src.split("/")[-1]  # e.g. "jsearch/linkedin" → "linkedin"
    return _SOURCE_DISPLAY.get(key, key.title())


def _stack_line(tags: list[str]) -> str:
    names = [_STACK_DISPLAY[t] for t in tags if t in _STACK_DISPLAY]
    return " · ".join(dict.fromkeys(names))


def _snippet(text: str, limit: int = SNIPPET_LEN) -> str:
    if not text:
        return ""
    t = text.strip()
    if len(t) > limit:
        t = t[:limit].rsplit(" ", 1)[0] + "…"
    return html.escape(t)


def format_message(job: Job) -> str:
    """Build the rich HTML-formatted message body for a single job."""
    tags = hashtags(job)
    lines: list[str] = []

    if is_profile_match(job):
        lines.append("⭐️ <b>PROFILE MATCH</b> ⭐️")
        lines.append("")

    # Headline: title + company, and where it came from.
    lines.append(f"☕ <b>{html.escape(job.title)}</b>")
    company = f"🏢 <b>{html.escape(job.company)}</b>" if job.company else ""
    company_line = " · ".join(x for x in [company, f"via {_source_name(job)}"] if x)
    lines.append(company_line)
    lines.append("")

    # Facts row(s): location, type, seniority, salary.
    facts = [_location_line(job)]
    if (etype := _employment_type(job)):
        facts.append(f"💼 {etype}")
    if (level := _seniority(job)):
        facts.append(f"📈 {level}")
    lines.append("   ".join(facts))
    if job.salary:
        lines.append(f"💰 <b>{html.escape(job.salary)}</b>")

    # Tech stack, highlighted.
    stack = _stack_line(tags)
    if stack:
        lines.append(f"🧰 {stack}")

    # Per-language fit meter(s): Java and/or Go, whichever the job matches.
    for label, score in (("☕ Java", java_fit(job)), ("🐹 Go", go_fit(job))):
        if score:
            filled = min(5, round(score / 8))
            meter = "🟩" * filled + "⬜" * (5 - filled)
            lines.append(f"{label} fit: {meter} ({score})")

    # Description snippet as a quote block.
    snippet = _snippet(job.description)
    if snippet:
        lines.append("")
        lines.append(f"<blockquote>{snippet}</blockquote>")

    # Call to action.
    lines.append("")
    lines.append(f'👉 <a href="{html.escape(job.url)}"><b>Apply now</b></a>')

    # Hashtags for in-channel search.
    src = source_hashtag(job)
    if src and src not in tags:
        tags.append(src)
    if tags:
        lines.append("")
        lines.append(" ".join(tags))

    return "\n".join(lines)[:MAX_MESSAGE_LEN]


DIGEST_SIZE = 10


def _display_location(job: Job) -> str:
    """Normalize the location to Worldwide / Remote (icon + label)."""
    low = job.location.lower()
    if re.search(r"\b(world\s?wide|anywhere|global)\b", low):
        return "🌍 Worldwide"
    if re.search(r"\b(europe|emea|eu)\b", low):
        return "🌍 Remote (Europe)"
    return "🌍 Remote"


def _bullet(job: Job) -> str:
    """A single clickable job line under its company heading."""
    star = "⭐ " if is_profile_match(job) else ""
    fit = ""
    if java_fit(job):
        fit = f" · ☕{java_fit(job)}"
    elif go_fit(job):
        fit = f" · 🐹{go_fit(job)}"
    tags = hashtags(job)
    reloc = " · ✈️relocation" if "#relocation" in tags else ""
    contract = " · 📄contract" if "#contract" in tags else ""
    src = source_hashtag(job)
    if src and src not in tags:
        tags.append(src)
    # Drop #onsite (all jobs are remote-workable) to keep the tag line tight.
    shown = [t for t in tags if t != "#onsite"][:7]
    tagline = "\n  " + " ".join(shown) if shown else ""
    return (f'• {star}<a href="{html.escape(job.url)}">{html.escape(job.title)}</a>'
            f" — {_display_location(job)}{fit}{reloc}{contract}{tagline}")


def format_digest(jobs: list[Job]) -> str:
    """Build one digest message: jobs grouped by company, titles as links."""
    jobs = jobs[:DIGEST_SIZE]
    # Group by company, preserving fit-sorted order.
    groups: dict[str, list[Job]] = {}
    order: list[str] = []
    for job in jobs:
        key = job.company or "Other"
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(job)

    blocks = []
    for company in order:
        cjobs = groups[company]
        head = (f"<b>{html.escape(company)}</b> · 🌐 "
                f"{html.escape(_source_name(cjobs[0]))}")
        bullets = "\n".join(_bullet(j) for j in cjobs)
        blocks.append(f"{head}\n{bullets}")

    header = f"📋 <b>Java &amp; Go jobs</b> · {len(jobs)} new"
    return (header + "\n\n" + "\n\n".join(blocks))[:MAX_MESSAGE_LEN]


def send_text(token: str, chat_id: str, text: str) -> bool:
    """Send a plain text message (used for failure/health alerts)."""
    url = API.format(token=token, method="sendMessage")
    try:
        resp = requests.post(
            url, data={"chat_id": chat_id, "text": text}, timeout=20
        )
        return resp.status_code == 200 and resp.json().get("ok", False)
    except requests.RequestException as exc:
        log.warning("Alert send failed: %s", exc)
        return False


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

    def post_digest(self, jobs: list[Job]) -> int | None:
        """Send one digest message (up to DIGEST_SIZE jobs, no image preview)."""
        text = format_digest(jobs)
        if self.dry_run:
            print("-" * 50)
            print(text)
            return DRY_RUN_MSG_ID
        payload = {
            "chat_id": self.channel,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,  # no link-preview images
        }
        markup = self._reply_markup()
        if markup:
            payload["reply_markup"] = markup
        url = API.format(token=self.token, method="sendMessage")
        try:
            resp = self._session.post(url, data=payload, timeout=20)
            data = resp.json() if resp.status_code == 200 else {}
            if data.get("ok"):
                return data["result"]["message_id"]
            log.warning("Telegram digest send failed: %s", resp.text[:200])
            return None
        except requests.RequestException as exc:
            log.warning("Telegram digest send error: %s", exc)
            return None

    def post(self, job: Job) -> int | None:
        """Send one job. Returns the Telegram message_id, or None on failure.

        In dry-run, prints the message and returns the sentinel DRY_RUN_MSG_ID.
        """
        text = format_message(job)
        if self.dry_run:
            print("-" * 50)
            print(text)
            if self.all_jobs_url:
                print(f"[button → {self.all_jobs_url}]")
            return DRY_RUN_MSG_ID

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
            data = resp.json() if resp.status_code == 200 else {}
            if data.get("ok"):
                return data["result"]["message_id"]
            log.warning("Telegram send failed for %s: %s", job.title, resp.text[:200])
            return None
        except requests.RequestException as exc:
            log.warning("Telegram send error for %s: %s", job.title, exc)
            return None

    def post_batch(self, jobs: list[Job]) -> list[tuple[Job, int]]:
        """Post jobs sequentially with a delay. Returns (job, message_id) sent."""
        results = []
        for i, job in enumerate(jobs):
            mid = self.post(job)
            if mid is not None:
                results.append((job, mid))
            if not self.dry_run and i < len(jobs) - 1:
                time.sleep(SEND_DELAY_SECONDS)
        return results

    def close_message(self, message_id: int, title: str, company: str, url: str) -> bool:
        """Edit a previously-posted job to mark it closed/expired."""
        text = (
            "🔴 <b>CLOSED · posting expired</b>\n\n"
            f"<s>☕ {html.escape(title)}</s>\n"
        )
        if company:
            text += f"🏢 {html.escape(company)}\n"
        text += f'🔗 <a href="{html.escape(url)}">Original posting</a>'
        if self.dry_run:
            print(f"[would mark CLOSED: msg {message_id} — {title}]")
            return True
        api = API.format(token=self.token, method="editMessageText")
        try:
            resp = self._session.post(api, data={
                "chat_id": self.channel,
                "message_id": message_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }, timeout=20)
            return resp.status_code == 200 and resp.json().get("ok", False)
        except requests.RequestException as exc:
            log.warning("Telegram close failed for msg %s: %s", message_id, exc)
            return False
