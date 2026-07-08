"""Detect skills/attributes in a job and produce Telegram hashtags."""
from __future__ import annotations

import re

from .models import Job

# Ordered so the most identifying tags come first. Each entry: (hashtag, patterns).
_TAGS: list[tuple[str, list[str]]] = [
    ("java", [r"\bjava\b"]),
    ("spring", [r"\bspring\b", r"\bspring boot\b"]),
    ("fullstack", [r"\bfull[\s-]?stack\b"]),
    ("angular", [r"\bangular\b"]),
    ("react", [r"\breact\b"]),
    ("ai", [r"\bai\b", r"\bmachine learning\b", r"\bml engineer\b", r"\bllm\b", r"\bgenai\b", r"\bnlp\b"]),
    ("aws", [r"\baws\b", r"\bamazon web services\b"]),
    ("gcp", [r"\bgcp\b", r"\bgoogle cloud\b"]),
    ("azure", [r"\bazure\b"]),
    ("kubernetes", [r"\bkubernetes\b", r"\bk8s\b"]),
    ("docker", [r"\bdocker\b"]),
    ("kafka", [r"\bkafka\b"]),
    ("microservices", [r"\bmicroservices?\b"]),
    ("kotlin", [r"\bkotlin\b"]),
    ("remote", [r"\bremote\b", r"\bworldwide\b", r"\banywhere\b"]),
    ("senior", [r"\bsenior\b", r"\bsr\.?\b", r"\bstaff\b", r"\bprincipal\b", r"\blead\b"]),
    ("junior", [r"\bjunior\b", r"\bjr\.?\b", r"\bentry[\s-]?level\b"]),
]

_COMPILED = [(tag, [re.compile(p) for p in pats]) for tag, pats in _TAGS]


def hashtags(job: Job) -> list[str]:
    """Return an ordered, de-duplicated list of hashtags for a job."""
    text = job.haystack
    found = []
    for tag, patterns in _COMPILED:
        if any(p.search(text) for p in patterns):
            found.append(f"#{tag}")
    # Make remote vs on-site explicit for filtering in the channel.
    if "#remote" not in found:
        found.append("#onsite")
    return found


def source_hashtag(job: Job) -> str:
    """Hashtag identifying where the job came from, e.g. #linkedin, #remotive.

    JSearch jobs carry a "jsearch/<publisher>" source, so we tag the publisher
    (LinkedIn/Indeed/...) rather than the aggregator itself.
    """
    src = job.source.lower()
    if "/" in src:
        src = src.split("/", 1)[1]
    src = re.sub(r"[^a-z0-9]", "", src)
    return f"#{src}" if src else ""


def is_profile_match(job: Job) -> bool:
    """True when the job hits the user's target profile (Angular/AWS/AI)."""
    tags = set(hashtags(job))
    return bool({"#angular", "#aws", "#ai"} & tags)
