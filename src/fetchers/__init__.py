"""Job source fetchers. Each module exposes fetch() -> list[Job]."""
from __future__ import annotations

import logging

from ..models import Job
from . import arbeitnow, jobicy, remoteok, remotive

log = logging.getLogger(__name__)

# Each fetcher runs independently; one failing source must not kill the run.
_SOURCES = [remotive, arbeitnow, jobicy, remoteok]


def fetch_all() -> list[Job]:
    """Fetch from every source, tolerating individual failures."""
    jobs: list[Job] = []
    for module in _SOURCES:
        name = module.__name__.split(".")[-1]
        try:
            found = module.fetch()
            log.info("%s: fetched %d jobs", name, len(found))
            jobs.extend(found)
        except Exception as exc:  # noqa: BLE001 - deliberately tolerant
            log.warning("%s: fetch failed (%s)", name, exc)
    return jobs
