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
    ("grpc", [r"\bgrpc\b", r"\bprotobuf\b"]),
    ("micronaut", [r"\bmicronaut\b"]),
    ("reactive", [r"\breactive\b", r"\bwebflux\b", r"\br2dbc\b"]),
    ("kotlin", [r"\bkotlin\b"]),
    ("postgres", [r"\bpostgres(ql)?\b"]),
    ("redis", [r"\bredis\b"]),
    ("eventdriven", [r"\bevent[\s-]driven\b"]),
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


# Standout skills from the target CV — a job hitting ≥2 (or any Go) is a match.
_PROFILE_STANDOUT = re.compile(
    r"\bgrpc\b|\bprotobuf\b|\bmicronaut\b|\bkafka\b|\breactive\b|\bwebflux\b"
    r"|\br2dbc\b|event[\s-]driven|\bkubernetes\b|\bgraalvm\b|\bmicroservices?\b",
    re.I,
)


def is_profile_match(job: Job) -> bool:
    """⭐ when the job strongly matches the CV: a Go role, or ≥2 standout skills
    (gRPC, Micronaut, Kafka, reactive, event-driven, Kubernetes, microservices)."""
    text = job.haystack
    if go_fit(job):
        return True
    return len(set(_PROFILE_STANDOUT.findall(text))) >= 2


# Backend skills that count toward either a Java or a Go role (CV-weighted).
_SHARED_FIT = [
    (r"\bmicroservices?\b", 7),
    (r"\bkafka\b", 6),
    (r"\bgrpc\b|\bprotobuf\b", 6),
    (r"\breactive\b|\bwebflux\b|\br2dbc\b", 5),
    (r"event[\s-]driven", 5),
    (r"\baws\b", 5),
    (r"\bkubernetes\b|\bk8s\b", 4),
    (r"\bdocker\b", 3),
    (r"\b(postgres|postgresql|redis|elasticsearch|mongodb)\b", 2),
]
_JAVA_FIT = [
    (r"\bjava\b", 10),
    (r"\bspring( boot)?\b", 10),
    (r"\bmicronaut\b", 8),
    (r"\bhibernate\b", 3),
    (r"\bkotlin\b", 2),
]
_GO_FIT = [(r"\bgolang\b", 10)]

_SHARED_RE = [(re.compile(p), w) for p, w in _SHARED_FIT]
_JAVA_FIT_RE = [(re.compile(p), w) for p, w in _JAVA_FIT]
_GO_FIT_RE = [(re.compile(p), w) for p, w in _GO_FIT]


def _score(text: str, specific: list) -> int:
    return (sum(w for r, w in specific if r.search(text))
            + sum(w for r, w in _SHARED_RE if r.search(text)))


def java_fit(job: Job) -> int:
    """Java-fit score, or 0 if the job isn't a Java role."""
    tags = hashtags(job)
    return _score(job.haystack, _JAVA_FIT_RE) if "#java" in tags else 0


def go_fit(job: Job) -> int:
    """Go-fit score, or 0 if the job isn't a Go role."""
    tags = hashtags(job)
    return _score(job.haystack, _GO_FIT_RE) if "#golang" in tags else 0


def relevance_score(job: Job) -> int:
    """Overall ranking score = the stronger of the Java and Go fits."""
    return max(java_fit(job), go_fit(job))
