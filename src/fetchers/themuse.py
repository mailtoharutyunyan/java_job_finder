"""The Muse public jobs API (free, no key): https://www.themuse.com/api/public/jobs

Returns software-engineering jobs (remote and on-site) across many companies;
filter.py narrows to Java roles.
"""
from __future__ import annotations

import logging

from ..http import get_json
from ..models import Job

log = logging.getLogger(__name__)

URL = "https://www.themuse.com/api/public/jobs"
PAGES = 2  # 20 results per page


def _parse_page(data: dict) -> list[Job]:
    results = data.get("results", []) if isinstance(data, dict) else []
    jobs = []
    for j in results:
        url = (j.get("refs") or {}).get("landing_page")
        if not url:
            continue
        locations = [l.get("name", "") for l in j.get("locations", [])]
        levels = [l.get("name", "") for l in j.get("levels", [])]
        cats = [c.get("name", "") for c in j.get("categories", [])]
        jobs.append(
            Job(
                title=j.get("name", ""),
                company=(j.get("company") or {}).get("name", ""),
                url=url,
                source="themuse",
                location=", ".join(loc for loc in locations if loc) or "Remote",
                tags=[t for t in levels + cats if t],
                description=j.get("contents", ""),
                published_at=j.get("publication_date", ""),
            )
        )
    return jobs


def fetch() -> list[Job]:
    jobs = []
    for page in range(1, PAGES + 1):
        try:
            data = get_json(URL, params={"category": "Software Engineering",
                                         "page": page})
            jobs.extend(_parse_page(data))
        except Exception as exc:  # noqa: BLE001 - one bad page shouldn't kill the rest
            log.warning("themuse: page %d failed (%s)", page, exc)
    return jobs
