"""NoDesk remote jobs RSS (free, no key): https://nodesk.co/remote-jobs/

Item titles are formatted "Position at Company".
"""
from __future__ import annotations

from ..http import get_rss_items
from ..models import Job

URL = "https://nodesk.co/remote-jobs/index.xml"


def _split_title(raw: str) -> tuple[str, str]:
    if " at " in raw:
        position, _, company = raw.rpartition(" at ")
        return position.strip(), company.strip()
    return raw.strip(), ""


def fetch() -> list[Job]:
    jobs = []
    for item in get_rss_items(URL):
        url = item.get("link")
        if not url:
            continue
        position, company = _split_title(item.get("title", ""))
        jobs.append(
            Job(
                title=position,
                company=company,
                url=url,
                source="nodesk",
                location="Remote",  # NoDesk lists only remote roles
                tags=[t for t in [item.get("category", "")] if t],
                description=item.get("description", ""),
                published_at=item.get("pubDate", ""),
            )
        )
    return jobs
