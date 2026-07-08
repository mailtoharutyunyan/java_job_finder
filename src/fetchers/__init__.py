"""Job source fetchers. Each module exposes fetch() -> list[Job]."""
from __future__ import annotations

import logging

from ..models import Job
from . import (
    arbeitnow,
    himalayas,
    jobicy,
    jsearch,
    remoteok,
    remotive,
    themuse,
    weworkremotely,
    workingnomads,
)

log = logging.getLogger(__name__)

# Each fetcher runs independently; one failing source must not kill the run.
# jsearch (LinkedIn/Indeed via RapidAPI) self-limits to stay under its quota
# and returns [] when no key is configured; all others are free and keyless.
_SOURCES = [
    remotive,
    arbeitnow,
    jobicy,
    remoteok,
    himalayas,
    weworkremotely,
    workingnomads,
    themuse,
    jsearch,
]


def fetch_all() -> tuple[list[Job], list[str]]:
    """Fetch from every source, tolerating individual failures.

    Returns (jobs, failed_source_names) so the caller can alert when sources
    break. jsearch skipping (no key / outside its window) is not a failure.
    """
    jobs: list[Job] = []
    failed: list[str] = []
    for module in _SOURCES:
        name = module.__name__.split(".")[-1]
        try:
            found = module.fetch()
            log.info("%s: fetched %d jobs", name, len(found))
            jobs.extend(found)
        except Exception as exc:  # noqa: BLE001 - deliberately tolerant
            log.warning("%s: fetch failed (%s)", name, exc)
            failed.append(name)
    return jobs, failed
