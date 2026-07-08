"""Jobicy remote jobs API: https://jobicy.com/api/v2/remote-jobs"""
from __future__ import annotations

from ..http import get_json
from ..models import Job

URL = "https://jobicy.com/api/v2/remote-jobs"


def _salary(j: dict) -> str:
    lo, hi = j.get("annualSalaryMin"), j.get("annualSalaryMax")
    cur = j.get("salaryCurrency", "")
    if lo and hi:
        return f"{cur} {lo}-{hi}".strip()
    if lo:
        return f"{cur} {lo}+".strip()
    return ""


def fetch() -> list[Job]:
    data = get_json(URL, params={"count": 50, "tag": "java"})
    jobs = data.get("jobs", []) if isinstance(data, dict) else []
    result = []
    for j in jobs:
        if not j.get("url"):
            continue
        industry = j.get("jobIndustry", [])
        job_type = j.get("jobType", [])
        tags = (industry if isinstance(industry, list) else [industry]) + (
            job_type if isinstance(job_type, list) else [job_type]
        )
        result.append(
            Job(
                title=j.get("jobTitle", ""),
                company=j.get("companyName", ""),
                url=j.get("url", ""),
                source="jobicy",
                location=j.get("jobGeo", ""),
                salary=_salary(j),
                tags=[str(t) for t in tags if t],
                description=j.get("jobExcerpt", "") or j.get("jobDescription", ""),
                published_at=j.get("pubDate", ""),
            )
        )
    return result
