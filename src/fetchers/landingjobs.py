"""Landing.jobs API (free, no key): https://landing.jobs/api/v1/jobs

Europe-focused board with an explicit `relocation_paid` flag — a strong fit for
relocation-seeking candidates.
"""
from __future__ import annotations

from ..http import get_json
from ..models import Job

URL = "https://landing.jobs/api/v1/jobs"


def _company_from_url(url: str) -> str:
    # https://landing.jobs/at/<company-slug>/<job-slug> → "<company slug>"
    parts = url.split("/at/")
    if len(parts) == 2:
        slug = parts[1].split("/")[0]
        return slug.replace("-", " ").title()
    return ""


def _location(j: dict) -> str:
    if j.get("remote"):
        return "Remote"
    locs = j.get("locations") or []
    bits = [f"{l.get('city', '')} {l.get('country_code', '')}".strip() for l in locs]
    return ", ".join(b for b in bits if b) or "Remote"


def _salary(j: dict) -> str:
    lo, hi, cur = j.get("gross_salary_low"), j.get("gross_salary_high"), j.get("currency_code", "")
    if lo and hi:
        return f"{cur} {lo}-{hi}".strip()
    return ""


def _to_jobs(items: list) -> list[Job]:
    jobs = []
    for j in items:
        url = j.get("url")
        if not url:
            continue
        desc_parts = [j.get("role_description", ""), j.get("main_requirements", ""),
                      j.get("nice_to_have", "")]
        # Surface the relocation flag as text so the filter/tagger detect it.
        if j.get("relocation_paid"):
            desc_parts.append("Relocation paid / visa sponsorship available.")
        jobs.append(
            Job(
                title=j.get("title", ""),
                company=_company_from_url(url),
                url=url,
                source="landingjobs",
                location=_location(j),
                salary=_salary(j),
                tags=j.get("tags", []) or [],
                description=" ".join(p for p in desc_parts if p),
                published_at=j.get("published_at", ""),
            )
        )
    return jobs


def fetch() -> list[Job]:
    data = get_json(URL, params={"limit": 50})
    items = data if isinstance(data, list) else data.get("jobs", [])
    return _to_jobs(items)
