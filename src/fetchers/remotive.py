"""Remotive free jobs API: https://remotive.com/api/remote-jobs"""
from __future__ import annotations

from ..http import get_json
from ..models import Job

URL = "https://remotive.com/api/remote-jobs"


def _to_jobs(jobs: list[dict]) -> list[Job]:
    return [
        Job(
            title=j.get("title", ""),
            company=j.get("company_name", ""),
            url=j.get("url", ""),
            source="remotive",
            location=j.get("candidate_required_location", ""),
            salary=j.get("salary", ""),
            tags=j.get("tags", []) or [],
            description=j.get("description", ""),
            published_at=j.get("publication_date", ""),
        )
        for j in jobs
        if j.get("url")
    ]


def fetch() -> list[Job]:
    # Broaden coverage by searching multiple Java-family terms.
    jobs = []
    for term in ("java", "spring boot"):
        data = get_json(URL, params={"search": term})
        jobs.extend(data.get("jobs", []) if isinstance(data, dict) else [])
    return _to_jobs(jobs)
