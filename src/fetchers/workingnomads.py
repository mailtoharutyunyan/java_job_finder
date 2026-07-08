"""Working Nomads jobs API (free, no key).

https://www.workingnomads.com/api/exposed_jobs/ returns a flat JSON list of
recent remote jobs across all categories; filter.py narrows to Java roles.
"""
from __future__ import annotations

from ..http import get_json
from ..models import Job

URL = "https://www.workingnomads.com/api/exposed_jobs/"


def fetch() -> list[Job]:
    data = get_json(URL)
    if not isinstance(data, list):
        return []
    result = []
    for j in data:
        url = j.get("url")
        if not url:
            continue
        tags_raw = j.get("tags") or ""
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
        if j.get("category_name"):
            tags.append(j["category_name"])
        result.append(
            Job(
                title=j.get("title", ""),
                company=j.get("company_name", ""),
                url=url,
                source="workingnomads",
                location=j.get("location", "") or "Remote",
                tags=tags,
                description=j.get("description", ""),
                published_at=j.get("pub_date", ""),
            )
        )
    return result
