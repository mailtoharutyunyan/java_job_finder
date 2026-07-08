"""Entry point: fetch → filter → dedupe → post → refresh page → save state.

Run modes:
  python -m src.main              normal hourly run
  python -m src.main --dry-run    print messages instead of posting (no secrets)
  python -m src.main --bootstrap  mark the current backlog as seen without posting
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

from . import fetchers
from .filter import filter_java
from .poster import TelegramPoster
from .state import SeenStore
from . import telegraph_page

MAX_POSTS_PER_RUN = 5

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("java-jobs")


def dedupe_by_key(jobs):
    seen, out = set(), []
    for j in jobs:
        if j.key in seen:
            continue
        seen.add(j.key)
        out.append(j)
    return out


def run(dry_run: bool = False, bootstrap: bool = False) -> int:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    channel = os.environ.get("TELEGRAM_CHANNEL_ID", "")
    tg_token = os.environ.get("TELEGRAPH_ACCESS_TOKEN")

    if not dry_run and (not token or not channel):
        log.error("TELEGRAM_BOT_TOKEN and TELEGRAM_CHANNEL_ID must be set.")
        return 1

    raw = fetchers.fetch_all()
    log.info("Fetched %d raw jobs", len(raw))

    java_jobs = dedupe_by_key(filter_java(raw))
    log.info("%d Java-family jobs after filtering", len(java_jobs))

    store = SeenStore()
    new_jobs = store.new_jobs(java_jobs)
    log.info("%d new (unseen) jobs", len(new_jobs))

    # Refresh the "all active jobs" page first so the button URL exists.
    page_url = telegraph_page.publish(java_jobs, tg_token, dry_run=dry_run)
    log.info("All-jobs page: %s", page_url or "(unavailable)")

    if bootstrap:
        for job in java_jobs:
            store.add(job)
        store.save()
        log.info("Bootstrap complete: marked %d jobs as seen, posted none.",
                 len(java_jobs))
        return 0

    to_post = new_jobs[:MAX_POSTS_PER_RUN]
    overflow = len(new_jobs) - len(to_post)
    if overflow > 0:
        log.info("Posting %d now; %d roll to next run.", len(to_post), overflow)

    poster = TelegramPoster(token, channel, all_jobs_url=page_url, dry_run=dry_run)
    sent = poster.post_batch(to_post)
    log.info("Posted %d/%d jobs", sent, len(to_post))

    # Only mark jobs we actually sent as seen, so failures retry next run.
    for job in to_post[:sent]:
        store.add(job)

    if not dry_run:
        store.save()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Java jobs → Telegram channel bot")
    parser.add_argument("--dry-run", action="store_true",
                        help="print formatted messages instead of posting")
    parser.add_argument("--bootstrap", action="store_true",
                        help="mark current jobs as seen without posting")
    args = parser.parse_args()
    return run(dry_run=args.dry_run, bootstrap=args.bootstrap)


if __name__ == "__main__":
    sys.exit(main())
