"""Company ATS feeds (free, no key): Greenhouse and Lever.

Pulls jobs straight from a curated list of Java-heavy employers' applicant
tracking systems. Greenhouse: boards-api.greenhouse.io/v1/boards/<c>/jobs.
Lever: api.lever.co/v0/postings/<c>. Add companies to the lists below.
"""
from __future__ import annotations

import html
import logging

from ..http import get_json
from ..models import Job

log = logging.getLogger(__name__)

GREENHOUSE = "https://boards-api.greenhouse.io/v1/boards/{c}/jobs?content=true"
LEVER = "https://api.lever.co/v0/postings/{c}?mode=json"

# Java-heavy companies with confirmed-working Greenhouse boards.
GREENHOUSE_COMPANIES = [
    "gitlab", "elastic", "mongodb", "datadog", "grafanalabs", "sofi",
    "airbnb", "dropbox", "twilio", "coinbase", "robinhood", "gusto", "brex",
]
LEVER_COMPANIES = [
    "netflix", "plaid",
]


def _greenhouse(company: str) -> list[Job]:
    data = get_json(GREENHOUSE.format(c=company))
    jobs = data.get("jobs", []) if isinstance(data, dict) else []
    result = []
    for j in jobs:
        url = j.get("absolute_url")
        if not url:
            continue
        result.append(
            Job(
                title=j.get("title", ""),
                company=j.get("company_name") or company.replace("-", " ").title(),
                url=url,
                source=f"greenhouse/{company}",
                location=(j.get("location") or {}).get("name", ""),
                description=html.unescape(j.get("content", "") or "")[:1500],
                published_at=j.get("updated_at", ""),
            )
        )
    return result


def _lever(company: str) -> list[Job]:
    data = get_json(LEVER.format(c=company))
    if not isinstance(data, list):
        return []
    result = []
    for j in data:
        url = j.get("hostedUrl") or j.get("applyUrl")
        if not url:
            continue
        cats = j.get("categories") or {}
        result.append(
            Job(
                title=j.get("text", ""),
                company=company.replace("-", " ").title(),
                url=url,
                source=f"lever/{company}",
                location=cats.get("location", ""),
                tags=[cats.get("team", ""), cats.get("commitment", "")],
                description=(j.get("descriptionPlain") or "")[:1000],
                published_at=str(j.get("createdAt", "")),
            )
        )
    return result


def fetch() -> list[Job]:
    jobs = []
    for company in GREENHOUSE_COMPANIES:
        try:
            jobs.extend(_greenhouse(company))
        except Exception as exc:  # noqa: BLE001 - one company shouldn't sink the rest
            log.warning("greenhouse/%s failed (%s)", company, exc)
    for company in LEVER_COMPANIES:
        try:
            jobs.extend(_lever(company))
        except Exception as exc:  # noqa: BLE001
            log.warning("lever/%s failed (%s)", company, exc)
    return jobs
