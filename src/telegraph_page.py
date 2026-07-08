"""Generate/refresh a Telegraph page listing all active jobs.

Telegraph (telegra.ph) is Telegram's own publishing service: pages open as
Instant View inside Telegram and need no backend. We create one page and then
edit it in place on every run so the URL (used by the "View all jobs" button)
stays stable. The page path is stored in telegraph_page.json (committed);
the access token lives in the TELEGRAPH_ACCESS_TOKEN secret.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import requests

from .models import Job
from .tagger import hashtags, is_profile_match, source_hashtag

log = logging.getLogger(__name__)

API = "https://api.telegra.ph/{method}"
PAGE_FILE = Path(__file__).resolve().parent.parent / "telegraph_page.json"
TITLE = "💼 Java Jobs — updated hourly"
AUTHOR = "Java Jobs Bot"


def _node(tag: str, children: list) -> dict:
    return {"tag": tag, "children": children}


def _job_nodes(jobs: list[Job]) -> list:
    """Build Telegraph DOM nodes for the job list."""
    content: list = []
    if not jobs:
        content.append(_node("p", ["No active jobs right now — check back soon."]))
        return content

    content.append(_node("p", [f"{len(jobs)} active Java jobs. Tap a title to apply."]))
    for job in jobs:
        badge = "⭐ " if is_profile_match(job) else ""
        meta_bits = [b for b in (job.company, job.location, job.salary) if b]
        link = _node("a", [f"{badge}{job.title}"])
        link["attrs"] = {"href": job.url, "target": "_blank"}
        para_children: list = [link]
        if meta_bits:
            para_children.append(_node("br", []))
            para_children.append(" · ".join(meta_bits))
        tags = hashtags(job)
        src = source_hashtag(job)
        if src and src not in tags:
            tags.append(src)
        if tags:
            para_children.append(_node("br", []))
            para_children.append(_node("i", [" ".join(tags)]))
        content.append(_node("p", para_children))
    return content


def _load_page() -> dict:
    if PAGE_FILE.exists():
        try:
            return json.loads(PAGE_FILE.read_text() or "{}")
        except json.JSONDecodeError:
            return {}
    return {}


def _save_page(data: dict) -> None:
    PAGE_FILE.write_text(json.dumps(data, indent=2))


def ensure_token(token: str | None) -> str | None:
    """Return a usable access token, creating an account if none is given."""
    if token:
        return token
    try:
        resp = requests.post(
            API.format(method="createAccount"),
            data={"short_name": "javajobs", "author_name": AUTHOR},
            timeout=20,
        ).json()
        if resp.get("ok"):
            new_token = resp["result"]["access_token"]
            log.warning(
                "Created a new Telegraph account. Save this as the "
                "TELEGRAPH_ACCESS_TOKEN secret to reuse the page:\n%s",
                new_token,
            )
            return new_token
    except requests.RequestException as exc:
        log.warning("Telegraph createAccount failed: %s", exc)
    return None


def publish(jobs: list[Job], token: str | None, dry_run: bool = False) -> str | None:
    """Create or edit the Telegraph page. Returns the page URL, or None."""
    content = _job_nodes(jobs)
    if dry_run:
        log.info("[dry-run] Telegraph page would list %d jobs", len(jobs))
        page = _load_page()
        return page.get("url")

    token = ensure_token(token)
    if not token:
        return None

    page = _load_page()
    path = page.get("path")
    content_json = json.dumps(content)

    try:
        if path:
            resp = requests.post(
                API.format(method="editPage"),
                data={
                    "access_token": token,
                    "path": path,
                    "title": TITLE,
                    "author_name": AUTHOR,
                    "content": content_json,
                    "return_content": "false",
                },
                timeout=20,
            ).json()
        else:
            resp = requests.post(
                API.format(method="createPage"),
                data={
                    "access_token": token,
                    "title": TITLE,
                    "author_name": AUTHOR,
                    "content": content_json,
                    "return_content": "false",
                },
                timeout=20,
            ).json()
    except requests.RequestException as exc:
        log.warning("Telegraph publish failed: %s", exc)
        return page.get("url")

    if not resp.get("ok"):
        log.warning("Telegraph API error: %s", resp)
        return page.get("url")

    result = resp["result"]
    data = {"path": result["path"], "url": result["url"]}
    _save_page(data)
    return data["url"]
