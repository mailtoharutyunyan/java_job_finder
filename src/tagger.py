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
    ("senior", [r"\bsenior\b", r"\bsr\.?\b", r"\bstaff\b", r"\bprincipal\b", r"\blead\b"]),
    ("junior", [r"\bjunior\b", r"\bjr\.?\b", r"\bentry[\s-]?level\b"]),
]

_RELOCATION_RE = re.compile(
    r"\b(relocation|relocate|visa|sponsorship|work permit)\b", re.I)

_COMPILED = [(tag, [re.compile(p) for p in pats]) for tag, pats in _TAGS]


def hashtags(job: Job) -> list[str]:
    """Return an ordered, de-duplicated list of hashtags for a job."""
    text = job.haystack
    found = []
    for tag, patterns in _COMPILED:
        if any(p.search(text) for p in patterns):
            found.append(f"#{tag}")
    # Go: "golang" anywhere, or bare "go" only in title/tags (never prose).
    struct = f"{job.title} {' '.join(job.tags)}".lower()
    if re.search(r"\bgolang\b", text) or re.search(r"\bgo\b", struct):
        found.append("#golang")
    # Remote vs on-site is judged from the location (not the description).
    found.append("#remote" if job.is_remote else "#onsite")
    if _RELOCATION_RE.search(job.description):
        found.append("#relocation")
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


# Weighted keywords for ranking a job's fit for a Java developer.
_SCORE_WEIGHTS: list[tuple[str, int]] = [
    (r"\bjava\b", 10),
    (r"\bgolang\b", 10),
    (r"\bspring( boot)?\b", 10),
    (r"\bmicroservices?\b", 7),
    (r"\bkafka\b", 5),
    (r"\baws\b", 5),
    (r"\bkubernetes\b|\bk8s\b", 4),
    (r"\bhibernate\b", 3),
    (r"\bdocker\b", 3),
    (r"\bangular\b", 3),
    (r"\b(ai|machine learning|llm|genai)\b", 3),
    (r"\bkotlin\b", 2),
]
_SCORE_RE = [(re.compile(p), w) for p, w in _SCORE_WEIGHTS]


def relevance_score(job: Job) -> int:
    """Higher = better fit for a Java developer (keyword-weighted)."""
    text = job.haystack
    return sum(w for r, w in _SCORE_RE if r.search(text))
