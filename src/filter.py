"""Java-family job filter with a JavaScript false-positive guard.

A job passes if it shows a genuine Java signal (core Java / Spring / JVM,
full-stack Java, or Java + AI). Titles that are really JavaScript/Node/React
roles are rejected unless they carry an independent Java signal.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from .models import Job

MAX_AGE_DAYS = 21  # only post jobs created within this many days

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
    r"\brust\b",
    r"\bc#",
    r"\.net\b",
    r"\bdotnet\b",
    r"\bscala\b",
    r"\belixir\b",
    r"\bdjango\b",
    r"\bflutter\b",
    r"\bdart\b",
    # Mobile roles use Java/Kotlin but aren't the backend Java jobs we want.
    r"\bandroid\b",
    r"\bios\b",
    r"\bmobile\b",
    r"\breact native\b",
    r"\bswift\b",
    r"\bobjective[\s-]?c\b",
    r"\bxamarin\b",
]

# Staffing / freelance-marketplace companies whose listings are generic
# "we use every technology" posts rather than a specific Java role.
_STAFFING_COMPANIES = {
    "lemon.io", "toptal", "turing", "andela", "crossover", "x-team", "xteam",
    "gun.io", "arc.dev", "arc", "braintrust", "proxify", "sowelo consulting",
    "sowelo", "deel", "remotasks", "scalable path", "scalablepath",
}

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


_GOLANG_RE = re.compile(r"\bgolang\b")   # unambiguous Go signal
_GO_WORD_RE = re.compile(r"\bgo\b")       # ambiguous ("go to market") — needs context


def _has_java(text: str) -> bool:
    return any(r.search(text) for r in _JAVA_RE)


def _title_is_offtopic(title: str) -> bool:
    """True when the TITLE names a competing stack and has no Java/Go signal."""
    t = title.lower()
    if _has_java(t) or _GOLANG_RE.search(t) or _GO_WORD_RE.search(t):
        return False
    return any(r.search(t) for r in _JS_RE)


def _title_is_dev_role(title: str) -> bool:
    t = title.lower()
    return any(r.search(t) for r in _DEV_TITLE_RE)


def _java_match(job: Job) -> bool:
    if _has_java(job.title.lower()):
        return True
    if _has_java(" ".join(job.tags)) or _has_java(job.description.lower()):
        return _title_is_dev_role(job.title)
    return False


def _go_match(job: Job) -> bool:
    """Match Go/Golang roles. "golang" is trusted; bare "go" needs a dev title
    (so "Go To Market Manager" doesn't slip in)."""
    title = job.title.lower()
    if _GOLANG_RE.search(title):
        return True
    tags = " ".join(job.tags).lower()
    if _GOLANG_RE.search(tags) or _GO_WORD_RE.search(tags):
        return _title_is_dev_role(job.title)
    if _GOLANG_RE.search(job.description.lower()):
        return _title_is_dev_role(job.title)
    if _GO_WORD_RE.search(title):
        return _title_is_dev_role(job.title)
    return False


def matches(job: Job) -> bool:
    """True if this is a Java- or Go-family job worth posting.

    A language signal in the title/tags is trusted; a description-only signal
    must be backed by an engineering-role title so product/data/design listings
    that merely dump a tech stack don't slip through.
    """
    if _title_is_offtopic(job.title):
        return False
    return _java_match(job) or _go_match(job)


# Title signals for roles that are NOT backend Java/Go engineering.
_OFF_ROLE = re.compile(
    r"\bsecurity\b|\bcyber|\bappsec\b|\bdevsecops\b"
    r"|full[\s-]?stack|fullstack"
    r"|front[\s-]?end"
    r"|\bdevops\b|site reliability|\bsre\b|\bplatform engineer\b|infrastructure"
    r"|\bqa\b|quality assurance|test engineer|\bsdet\b|\btester\b|automation test"
    r"|data engineer|data scientist|machine learning|\bml\b|analytics|data analyst"
    r"|architect|solutions? engineer|sales engineer|pre[\s-]?sales"
    r"|\bmanager\b|\bdirector\b|head of|vice president|\bvp\b|\bchief\b"
    r"|support|customer|content|curriculum|marketing|\bdesigner\b|recruit",
    re.I,
)

# Seniority levels outside the target mid/senior band.
_OFF_SENIORITY = re.compile(
    r"\bprincipal\b|\bstaff\b|\blead\b|\bdistinguished\b|\bhead\b"
    r"|\bjunior\b|\bjr\.?\b|\bintern(ship)?\b|entry[\s-]?level|\bgraduate\b"
    r"|\btrainee\b|\bapprentice\b",
    re.I,
)


def is_backend_dev_role(job: Job) -> bool:
    """True only for mid/senior backend Java/Go engineering titles.

    Excludes security, full-stack, front-end, DevOps/SRE, QA, data/ML,
    architect/solutions/sales, management, and out-of-band seniority
    (principal/staff/lead and junior/intern).
    """
    title = job.title
    if _OFF_ROLE.search(title):
        return False
    if _OFF_SENIORITY.search(title):
        return False
    return True


def is_staffing(job: Job) -> bool:
    """True if the employer is a staffing/freelance marketplace (generic posts)."""
    company = job.company.strip().lower()
    if not company:
        return False
    return any(s == company or s in company.split() or company.startswith(s)
               for s in _STAFFING_COMPANIES)


# Regions a person in Armenia can realistically work in remotely.
_ARMENIA_OK_REGION = re.compile(
    r"\b(world\s?wide|anywhere|global|international|emea|europe|"
    r"european|cet|eet|armenia|yerevan|caucasus|middle east)\b",
    re.I,
)

# Region-locked signals that exclude someone based in Armenia (unless the role
# also offers relocation/visa, which is checked separately).
_REGION_LOCKED = re.compile(
    r"\b(us[\s-]?only|u\.s\.?[\s-]?only|usa only|united states only|"
    r"canada only|india only|uk only|us based|must be based in|"
    r"authorized to work in the u)\b",
    re.I,
)


def _parse_date(raw: str) -> datetime | None:
    """Parse the many published_at formats sources use → aware datetime or None.

    Handles RFC-822 (RSS pubDate), ISO-8601 (with Z), and unix timestamps in
    seconds or milliseconds.
    """
    if not raw:
        return None
    raw = raw.strip()
    # Unix timestamp (seconds or milliseconds).
    if raw.isdigit():
        ts = int(raw)
        if ts > 1e12:  # milliseconds
            ts /= 1000
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        except (ValueError, OSError):
            return None
    # ISO-8601.
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    # RFC-822 (e.g. "Wed, 08 Jul 2026 20:07:47 +0000").
    try:
        dt = parsedate_to_datetime(raw)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def is_recent(job: Job, max_age_days: int = MAX_AGE_DAYS) -> bool:
    """True if the job was created within max_age_days. Unknown dates pass
    (we don't drop a job just because its source omitted a date)."""
    posted = _parse_date(job.published_at)
    if posted is None:
        return True
    age = (datetime.now(timezone.utc) - posted).days
    return age <= max_age_days


# Signals that the candidate must ALREADY hold a work permit / authorization
# (i.e. the employer won't sponsor) — someone in Armenia can't meet these.
_NO_PERMIT = re.compile(
    r"no\s+(visa\s+)?sponsorship"
    r"|not\s+(able\s+to\s+|going\s+to\s+)?sponsor"
    r"|unable\s+to\s+sponsor"
    r"|(cannot|can't|will not|won't|do not|don't|does not|doesn't|are not able to)"
    r"\s+(offer\s+|provide\s+)?(visa\s+)?sponsor"
    r"|without\s+(visa\s+)?sponsorship"
    r"|no\s+work\s+permit"
    r"|must\s+(be\s+)?(legally\s+)?(authorized|authorised|eligible)\s+to\s+work"
    r"|must\s+(already\s+)?have\s+(the\s+)?(right|authorization|authorisation|permit)\s+to\s+work"
    r"|(valid\s+)?work\s+(permit|authorization|authorisation)\s+(is\s+)?required"
    r"|existing\s+work\s+(permit|authorization|authorisation)",
    re.I,
)


def requires_work_permit(job: Job) -> bool:
    """True if the listing says the candidate must already be work-authorized."""
    return bool(_NO_PERMIT.search(job.description))


def offers_relocation(job: Job) -> bool:
    # A negated form ("no visa sponsorship") is NOT an offer of relocation.
    if requires_work_permit(job):
        return False
    return any(r.search(job.description.lower()) for r in _RELOCATION_RE)


def is_remote_or_relocation(job: Job) -> bool:
    """True if the job is remote (by location/tags) or offers relocation/visa."""
    return job.is_remote or offers_relocation(job)


def workable_from_armenia(job: Job) -> bool:
    """True if someone based in Armenia could realistically take this job.

    Accepts: relocation/visa roles, roles in Armenia, and remote roles open to
    a region that includes Armenia (worldwide / Europe / EMEA / unspecified).
    Rejects: on-site roles abroad, and remote roles locked to another region
    (e.g. "US only") with no relocation.
    """
    where = f"{job.location} {' '.join(job.tags)}".lower()

    # Requires the candidate to already hold a work permit / authorization,
    # and doesn't sponsor → someone in Armenia can't take it.
    if requires_work_permit(job):
        return False

    # Willing-to-move or already in-region always qualifies.
    if offers_relocation(job):
        return True
    if re.search(r"\barmenia\b|\byerevan\b", where):
        return True

    # Region-locked to somewhere else (e.g. "US only") → not workable.
    if _REGION_LOCKED.search(where) or _REGION_LOCKED.search(job.description.lower()):
        return False

    # Open to an Armenia-friendly region (Europe / EMEA / worldwide / …).
    # Checked regardless of the "remote" wording, because some remote boards
    # list allowed regions (e.g. "Northern America, LATAM, Europe, APAC")
    # instead of the word "remote".
    if _ARMENIA_OK_REGION.search(where):
        return True

    if job.is_remote:
        # A bare "Remote" with a single foreign country named → not workable;
        # otherwise treat unspecified remote as open.
        return not re.search(
            r"\b(united states|usa|u\.s\.|canada|india|brazil|australia|"
            r"philippines|nigeria|mexico|argentina|singapore|japan)\b", where)

    # On-site abroad with no relocation → not workable from Armenia.
    return False


def filter_java(jobs: list[Job]) -> list[Job]:
    """Java-family jobs a person in Armenia can take, excluding staffing.

    Keeps remote roles open to Armenia's region, relocation/visa roles, and
    roles located in Armenia; drops on-site-abroad and region-locked roles.
    """
    # Staffing/freelance marketplaces (Toptal, Lemon.io, …) are allowed —
    # the user is open to B2B/contract, and the backend-role + Java/Go filters
    # keep out those marketplaces' non-matching listings anyway.
    return [
        j for j in jobs
        if matches(j) and is_backend_dev_role(j)
        and workable_from_armenia(j) and is_recent(j)
    ]
