"""RemoteOK API: https://remoteok.com/api

The response is a list whose first element is a legal/metadata notice
(no "id"/"position"), which we skip.
"""
from __future__ import annotations

from ..http import get_json
from ..models import Job

URL = "https://remoteok.com/api"


def _salary(j: dict) -> str:
    lo, hi = j.get("salary_min"), j.get("salary_max")
    if lo and hi:
        return f"${lo}-${hi}"
    return ""


def _parse(data) -> list[Job]:
    if not isinstance(data, list):
        return []
    result = []
    for j in data:
        if not isinstance(j, dict) or not j.get("position") or not j.get("url"):
            continue
        result.append(
            Job(
                title=j.get("position", ""),
                company=j.get("company", ""),
                url=j.get("url", ""),
                source="remoteok",
                location=j.get("location", "") or "Remote",
                salary=_salary(j),
                tags=j.get("tags", []) or [],
                description=j.get("description", ""),
                published_at=j.get("date", ""),
            )
        )
    return result


def fetch() -> list[Job]:
    jobs = []
    for tag in ("java", "golang"):
        jobs.extend(_parse(get_json(URL, params={"tags": tag})))
    return jobs
