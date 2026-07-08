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

# Signals that, in a TITLE with no Java signal, indicate a non-Java role:
# JavaScript/frontend stacks and other competing primary languages. Used to
# reject jobs that only carry "java" via polluted tags (e.g. a RemoteOK
# "Python Developer" also tagged java).
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
    r"\bangular\b",
    r"\bfront[\s-]?end\b",
    # competing primary languages
    r"\bpython\b",
    r"\bruby\b",
    r"\brails\b",
    r"\bphp\b",
    r"\blaravel\b",
    r"\bgolang\b",
    r"\bgo developer\b",
    r"\brust\b",
    r"\bc#",
    r"\.net\b",
    r"\bdotnet\b",
    r"\bscala\b",
    r"\belixir\b",
    r"\bdjango\b",
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

# Location acceptability: remote/worldwide roles, plus roles that offer
# relocation or visa sponsorship.
_REMOTE_SIGNALS = [
    r"\bremote\b",
    r"\bworld[\s-]?wide\b",
    r"\banywhere\b",
    r"\bwork from home\b",
    r"\bwfh\b",
    r"\bdistributed\b",
    r"\bfully remote\b",
    r"\bremote[\s-]?first\b",
    r"\bhome[\s-]?office\b",
]
_RELOCATION_SIGNALS = [
    r"\brelocation\b",
    r"\brelocate\b",
    r"\brelo\b",
    r"\bvisa\b",
    r"\bsponsorship\b",
    r"\bwork permit\b",
]

_JAVA_RE = [re.compile(p) for p in _JAVA_SIGNALS]
_JS_RE = [re.compile(p) for p in _JS_SIGNALS]
_DEV_TITLE_RE = [re.compile(p) for p in _DEV_TITLE_SIGNALS]
_REMOTE_RE = [re.compile(p) for p in _REMOTE_SIGNALS]
_RELOCATION_RE = [re.compile(p) for p in _RELOCATION_SIGNALS]


def _has_java(text: str) -> bool:
    return any(r.search(text) for r in _JAVA_RE)


def _title_is_non_java(title: str) -> bool:
    """True when the TITLE names a competing stack and has no Java signal."""
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
    # Reject titles naming a competing stack (JS/Python/…) with no Java signal.
    if _title_is_non_java(job.title):
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


def is_remote_or_relocation(job: Job) -> bool:
    """True if the job is remote/worldwide or offers relocation/visa support.

    Location and tags are the primary signal; the description is included so
    roles that state "remote" or "visa sponsorship" only in the body still pass.
    """
    where = " ".join([job.location, " ".join(job.tags)]).lower()
    if any(r.search(where) for r in _REMOTE_RE):
        return True
    body = job.haystack
    if any(r.search(body) for r in _REMOTE_RE):
        return True
    return any(r.search(body) for r in _RELOCATION_RE)


def filter_java(jobs: list[Job]) -> list[Job]:
    """Java-family jobs that are also remote/worldwide or offer relocation."""
    return [j for j in jobs if matches(j) and is_remote_or_relocation(j)]
