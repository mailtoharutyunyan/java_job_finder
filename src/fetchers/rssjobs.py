"""Generic RSS job-feed fetcher for boards that expose a standard RSS feed.

Add a feed by appending (source_name, url) to FEEDS. Titles formatted
"Role at Company" or "Company: Role" are split when no <company> field exists.
Each feed is fetched independently so one broken feed can't sink the rest.
"""
from __future__ import annotations

import logging

from ..http import get_rss_items
from ..models import Job

log = logging.getLogger(__name__)

_RFJ = "https://remotefirstjobs.com/rss/jobs/{}.rss"
_RFJ_SKILLS = [
    "java", "backend", "kotlin", "microservices", "aws", "docker",
    "kubernetes", "cloud", "backend-engineer", "golang", "go",
    "devops", "cloud-engineer",
]

FEEDS: list[tuple[str, str]] = [
    ("remoteyeah", "https://remoteyeah.com/rss.xml"),
    ("tryremotely", "https://tryremotely.com/feeds/engineering-jobs.rss"),
    ("tryremotely", "https://tryremotely.com/feeds/jobs.rss"),
    ("euremotejobs", "https://euremotejobs.com/?feed=job_feed"),
    ("jobspresso", "https://jobspresso.co/?feed=job_feed"),
    ("jobscollider", "https://jobscollider.com/remote-software-development-jobs.rss"),
    ("jobscollider", "https://jobscollider.com/remote-devops-jobs.rss"),
    # General Remote First Jobs feed (all recent postings, filtered by us).
    ("remotefirstjobs", "https://remotefirstjobs.com/rss/jobs.rss"),
] + [("remotefirstjobs", _RFJ.format(s)) for s in _RFJ_SKILLS]


def _title_company(item: dict) -> tuple[str, str]:
    raw = (item.get("title") or "").strip()
    company = (item.get("company") or "").strip()
    if " at " in raw:
        position, _, tail = raw.rpartition(" at ")
        return position.strip(), company or tail.strip()
    if not company and ": " in raw:
        comp, _, position = raw.partition(": ")
        return position.strip(), comp.strip()
    return raw, company


def _tags(item: dict) -> list[str]:
    tags = [t.strip() for t in (item.get("tags") or "").split(",") if t.strip()]
    if item.get("category"):
        tags.append(item["category"].strip())
    return tags


def _parse_feed(source: str, items: list[dict]) -> list[Job]:
    jobs = []
    for item in items:
        url = item.get("link") or item.get("guid")
        if not url or not url.startswith("http"):
            continue
        position, company = _title_company(item)
        jobs.append(
            Job(
                title=position,
                company=company,
                url=url,
                source=source,
                location=(item.get("location") or item.get("region") or "Remote"),
                tags=_tags(item),
                description=item.get("description") or item.get("encoded", ""),
                published_at=item.get("pubDate", ""),
            )
        )
    return jobs


def fetch() -> list[Job]:
    jobs = []
    for source, url in FEEDS:
        try:
            jobs.extend(_parse_feed(source, get_rss_items(url)))
        except Exception as exc:  # noqa: BLE001 - one bad feed shouldn't kill the rest
            log.warning("rssjobs: feed %s failed (%s)", url, exc)
    return jobs
