"""JSearch aggregator (RapidAPI): surfaces LinkedIn / Indeed / Glassdoor jobs.

Requires a free RapidAPI key in the RAPIDAPI_KEY env var. The free tier allows
~200 requests/month, so this fetcher only queries on a few fixed UTC hours per
day (every 4h ≈ 180/month) to stay within quota. The other free sources keep
running every hour. Set JSEARCH_FORCE=1 to bypass the window (e.g. for a
manual/dry run).
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from ..http import get_json
from ..models import Job

log = logging.getLogger(__name__)

URL = "https://jsearch.p.rapidapi.com/search"
HOST = "jsearch.p.rapidapi.com"
QUERY = "java developer"

# Six evenly spaced UTC hours → ~180 requests/month, under the free-tier cap.
QUOTA_HOURS = {0, 4, 8, 12, 16, 20}


def _should_run() -> bool:
    """Fire at most once per quota window.

    The schedule runs every 15 min, so we also require the first quarter of the
    hour (minute < 15) to avoid 4 calls per qualifying hour blowing the quota.
    """
    if os.environ.get("JSEARCH_FORCE") == "1":
        return True
    now = datetime.now(timezone.utc)
    return now.hour in QUOTA_HOURS and now.minute < 15


def _salary(j: dict) -> str:
    lo, hi = j.get("job_min_salary"), j.get("job_max_salary")
    cur = j.get("job_salary_currency") or ""
    period = j.get("job_salary_period") or ""
    if lo and hi:
        return f"{cur} {int(lo)}-{int(hi)} {period}".strip()
    return ""


def _location(j: dict) -> str:
    if j.get("job_is_remote"):
        return "Remote"
    bits = [j.get("job_city"), j.get("job_state"), j.get("job_country")]
    return ", ".join(b for b in bits if b)


def _to_jobs(data: dict) -> list[Job]:
    """Parse a JSearch /search response into Job objects (pure, testable)."""
    items = data.get("data", []) if isinstance(data, dict) else []
    result = []
    for j in items:
        url = j.get("job_apply_link") or j.get("job_google_link")
        if not url:
            continue
        publisher = j.get("job_publisher") or "jsearch"
        emp_type = j.get("job_employment_type") or ""
        result.append(
            Job(
                title=j.get("job_title", ""),
                company=j.get("employer_name", ""),
                url=url,
                source=f"jsearch/{publisher}".lower(),
                location=_location(j),
                salary=_salary(j),
                tags=[emp_type] if emp_type else [],
                description=j.get("job_description", ""),
                published_at=j.get("job_posted_at_datetime_utc", ""),
            )
        )
    return result


def fetch() -> list[Job]:
    key = os.environ.get("RAPIDAPI_KEY")
    if not key:
        log.info("jsearch: RAPIDAPI_KEY not set, skipping")
        return []
    if not _should_run():
        log.info("jsearch: outside quota window (UTC hour), skipping")
        return []

    headers = {"X-RapidAPI-Key": key, "X-RapidAPI-Host": HOST}
    params = {
        "query": QUERY,
        "page": "1",
        "num_pages": "1",
        "date_posted": "week",
    }
    data = get_json(URL, params=params, headers=headers)
    return _to_jobs(data)
