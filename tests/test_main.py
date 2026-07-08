"""Tests for orchestration helpers (no network)."""
from src.main import interleave_by_source
from src.models import Job


def job(n, source):
    return Job(title=f"Java Dev {n}", company=f"Co{n}",
               url=f"https://x/{source}/{n}", source=source)


def test_interleave_round_robins_sources():
    # 5 from a dominant source, 1 each from two others.
    jobs = ([job(i, "remotefirstjobs") for i in range(5)]
            + [job(0, "remoteyeah"), job(0, "landingjobs")])
    out = interleave_by_source(jobs)
    # First three should hit three different sources.
    first_three = {j.source for j in out[:3]}
    assert first_three == {"remotefirstjobs", "remoteyeah", "landingjobs"}
    assert len(out) == len(jobs)


def test_interleave_groups_ats_sources():
    jobs = [job(0, "greenhouse/gitlab"), job(1, "lever/netflix")]
    out = interleave_by_source(jobs)
    # Both map to the "ats" bucket, so they don't jump ahead of each other oddly.
    assert len(out) == 2
