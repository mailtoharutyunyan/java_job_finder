"""Tests for JSearch response parsing and quota gating (no network)."""
import os
from unittest import mock

from src.fetchers import jsearch
from src.filter import matches

SAMPLE = {
    "status": "OK",
    "data": [
        {
            "job_title": "Senior Java Developer",
            "employer_name": "Acme Corp",
            "job_publisher": "LinkedIn",
            "job_apply_link": "https://www.linkedin.com/jobs/view/123",
            "job_employment_type": "FULLTIME",
            "job_is_remote": True,
            "job_city": "Berlin",
            "job_country": "DE",
            "job_min_salary": 70000,
            "job_max_salary": 90000,
            "job_salary_currency": "EUR",
            "job_salary_period": "YEAR",
            "job_description": "Java, Spring Boot, AWS, Angular.",
            "job_posted_at_datetime_utc": "2026-07-08T10:00:00.000Z",
        },
        {
            # No apply link and no google link → skipped.
            "job_title": "Java Engineer",
            "employer_name": "NoLink Inc",
            "job_description": "Java role",
        },
    ],
}


def test_parse_basic_fields():
    jobs = jsearch._to_jobs(SAMPLE)
    assert len(jobs) == 1  # second item skipped (no url)
    job = jobs[0]
    assert job.title == "Senior Java Developer"
    assert job.company == "Acme Corp"
    assert job.url == "https://www.linkedin.com/jobs/view/123"
    assert job.source == "jsearch/linkedin"
    assert job.location == "Remote"
    assert "EUR" in job.salary
    assert matches(job)  # passes the Java filter


def test_parse_empty():
    assert jsearch._to_jobs({"data": []}) == []
    assert jsearch._to_jobs({}) == []


def test_fetch_skips_without_key(monkeypatch):
    monkeypatch.delenv("RAPIDAPI_KEY", raising=False)
    assert jsearch.fetch() == []


def test_quota_gate_allows_configured_hours():
    with mock.patch.object(jsearch, "datetime") as m:
        m.now.return_value = mock.Mock(hour=4, minute=0)   # in window, first quarter
        assert jsearch._should_run() is True
        m.now.return_value = mock.Mock(hour=4, minute=30)  # right hour, later quarter
        assert jsearch._should_run() is False
        m.now.return_value = mock.Mock(hour=3, minute=0)   # wrong hour
        assert jsearch._should_run() is False


def test_quota_gate_force_override(monkeypatch):
    monkeypatch.setenv("JSEARCH_FORCE", "1")
    assert jsearch._should_run() is True
