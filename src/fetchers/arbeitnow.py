"""Arbeitnow free job board API: https://www.arbeitnow.com/api/job-board-api

The API returns all recent jobs with no server-side search, so we return
everything here and let filter.py narrow to Java-family roles.
"""
from __future__ import annotations

from ..http import get_json
from ..models import Job

URL = "https://www.arbeitnow.com/api/job-board-api"


def fetch() -> list[Job]:
    data = get_json(URL)
    jobs = data.get("data", []) if isinstance(data, dict) else []
    return [
        Job(
            title=j.get("title", ""),
            company=j.get("company_name", ""),
            url=j.get("url", ""),
            source="arbeitnow",
            location=j.get("location", ""),
            salary=j.get("salary", "") or "",
            tags=(j.get("tags", []) or []) + (j.get("job_types", []) or []),
            description=j.get("description", ""),
            published_at=str(j.get("created_at", "")),
        )
        for j in jobs
        if j.get("url")
    ]
