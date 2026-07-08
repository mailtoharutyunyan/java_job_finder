"""Java-family job filter with a JavaScript false-positive guard.

A job passes if it shows a genuine Java signal (core Java / Spring / JVM,
full-stack Java, or Java + AI). Titles that are really JavaScript/Node/React
roles are rejected unless they carry an independent Java signal.
"""
from __future__ import annotations

import re

from .models import Job

# Genuine Java signals. Word boundaries keep "java" from matching "javascript".
_JAVA_SIGNALS = [
    r"\bjava\b",
    r"\bspring\b",
    r"\bspring boot\b",
    r"\bjvm\b",
    r"\bj2ee\b",
    r"\bjakarta\b",
    r"\bhibernate\b",
    r"\bquarkus\b",
    r"\bmicronaut\b",
]

# JavaScript-family signals that, on their own, indicate a non-Java role.
_JS_SIGNALS = [
    r"\bjavascript\b",
    r"\bjs\b",
    r"\bnode\.?js\b",
    r"\bnode\b",
    r"\breact\b",
    r"\breact\.?js\b",
    r"\bvue\b",
    r"\btypescript\b",
    r"\bnext\.?js\b",
]

# Titles that indicate an actual software-engineering role. Used to keep
# description-only Java mentions from matching PM/data-science/design jobs
# whose listings merely dump a full tech stack into the description.
_DEV_TITLE_SIGNALS = [
    r"\bdeveloper\b",
    r"\bengineer\b",
    r"\bprogrammer\b",
    r"\barchitect\b",
    r"\bsde\b",
    r"\bsoftware\b",
    r"\bbackend\b",
    r"\bback[\s-]?end\b",
    r"\bfull[\s-]?stack\b",
    r"\bdevelopment\b",
    r"\bcoder\b",
]

_JAVA_RE = [re.compile(p) for p in _JAVA_SIGNALS]
_JS_RE = [re.compile(p) for p in _JS_SIGNALS]
_DEV_TITLE_RE = [re.compile(p) for p in _DEV_TITLE_SIGNALS]


def _has_java(text: str) -> bool:
    return any(r.search(text) for r in _JAVA_RE)


def _title_is_javascript(title: str) -> bool:
    """True when the TITLE is a JavaScript role with no Java signal of its own."""
    t = title.lower()
    if _has_java(t):
        return False
    return any(r.search(t) for r in _JS_RE)


def _title_is_dev_role(title: str) -> bool:
    t = title.lower()
    return any(r.search(t) for r in _DEV_TITLE_RE)


def matches(job: Job) -> bool:
    """Return True if this is a Java-family job worth posting.

    A Java signal in the title or tags is trusted outright. A Java signal that
    appears only in the free-text description must be backed by an
    engineering-role title — otherwise product/data/design listings that dump a
    full tech stack into their description would slip through.
    """
    # Reject JavaScript-titled roles that lack an independent Java signal.
    if _title_is_javascript(job.title):
        return False

    # A Java signal in the title is trusted outright.
    if _has_java(job.title.lower()):
        return True

    # A signal only in tags/description must be backed by an engineering-role
    # title, or marketplace listings (PM, data science, design) that tag/list a
    # full stack would slip through.
    if _has_java(" ".join(job.tags)) or _has_java(job.description.lower()):
        return _title_is_dev_role(job.title)

    return False


def filter_java(jobs: list[Job]) -> list[Job]:
    return [j for j in jobs if matches(j)]
