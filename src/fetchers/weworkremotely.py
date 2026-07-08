"""WeWorkRemotely RSS feeds (free, no key).

WWR exposes per-category RSS. We read the back-end and full-stack programming
feeds; item titles are formatted "Company: Position".
"""
from __future__ import annotations

import logging
from xml.etree import ElementTree as ET

from ..http import get_text
from ..models import Job

log = logging.getLogger(__name__)

FEEDS = [
    "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
    "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
]


def _split_title(raw: str) -> tuple[str, str]:
    """"Company: Position" → (company, position); falls back to ("", raw)."""
    if ": " in raw:
        company, _, position = raw.partition(": ")
        return company.strip(), position.strip()
    return "", raw.strip()


def _parse_feed(xml: str) -> list[Job]:
    root = ET.fromstring(xml)
    jobs = []
    for item in root.findall(".//item"):
        def text(tag: str) -> str:
            el = item.find(tag)
            return el.text if el is not None and el.text else ""

        url = text("link")
        if not url:
            continue
        company, position = _split_title(text("title"))
        jobs.append(
            Job(
                title=position,
                company=company,
                url=url,
                source="weworkremotely",
                location=text("region") or "Remote",
                tags=[t for t in [text("category")] if t],
                description=text("description"),
                published_at=text("pubDate"),
            )
        )
    return jobs


def fetch() -> list[Job]:
    jobs = []
    for feed in FEEDS:
        try:
            jobs.extend(_parse_feed(get_text(feed)))
        except Exception as exc:  # noqa: BLE001 - one bad feed shouldn't kill the rest
            log.warning("weworkremotely: feed failed (%s)", exc)
    return jobs
