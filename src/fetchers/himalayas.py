"""Himalayas remote jobs API (free, no key): https://himalayas.app/jobs/api"""
from __future__ import annotations

from ..http import get_json
from ..models import Job

URL = "https://himalayas.app/jobs/api"


def _salary(j: dict) -> str:
    lo, hi = j.get("minSalary"), j.get("maxSalary")
    cur = j.get("currency") or ""
    period = j.get("salaryPeriod") or ""
    if lo and hi:
        return f"{cur} {int(lo)}-{int(hi)} {period}".strip()
    return ""


def fetch() -> list[Job]:
    data = get_json(URL, params={"limit": 100})
    jobs = data.get("jobs", []) if isinstance(data, dict) else []
    result = []
    for j in jobs:
        url = j.get("applicationLink") or j.get("guid")
        if not url:
            continue
        locations = j.get("locationRestrictions") or []
        tags = (j.get("categories") or []) + (j.get("seniority") or [])
        result.append(
            Job(
                title=j.get("title", ""),
                company=j.get("companyName", ""),
                url=url,
                source="himalayas",
                location=", ".join(locations) if locations else "Remote",
                salary=_salary(j),
                tags=[str(t) for t in tags if t],
                description=j.get("excerpt", "") or j.get("description", ""),
                published_at=str(j.get("pubDate", "")),
            )
        )
    return result
