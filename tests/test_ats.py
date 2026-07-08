"""Tests for ATS (Greenhouse/Lever) parsing (no network)."""
from src.fetchers import ats
from src.filter import matches

GH = {
    "jobs": [
        {
            "title": "Senior Backend Engineer, Java",
            "company_name": "GitLab",
            "absolute_url": "https://boards.greenhouse.io/gitlab/jobs/123",
            "location": {"name": "Remote, EMEA"},
            "content": "&lt;p&gt;Build with Java, Spring Boot and Kafka.&lt;/p&gt;",
            "updated_at": "2026-07-08T10:00:00Z",
        },
        {"title": "No URL", "company_name": "X"},  # skipped
    ]
}

LEVER = [
    {
        "text": "Staff Software Engineer",
        "hostedUrl": "https://jobs.lever.co/cloudflare/abc",
        "categories": {"location": "Lisbon", "team": "Platform", "commitment": "Full Time"},
        "descriptionPlain": "Java and JVM services at scale.",
        "createdAt": 1720435200000,
    }
]


def test_greenhouse_parse_and_unescape(monkeypatch):
    monkeypatch.setattr("src.fetchers.ats.get_json",
                        lambda url, params=None, headers=None: GH)
    result = ats._greenhouse("gitlab")
    assert len(result) == 1
    job = result[0]
    assert job.company == "GitLab"
    assert job.source == "greenhouse/gitlab"
    assert "Spring Boot" in job.description  # HTML entities unescaped + tags stripped
    assert matches(job)


def test_lever_parse(monkeypatch):
    monkeypatch.setattr("src.fetchers.ats.get_json",
                        lambda url, params=None, headers=None: LEVER)
    result = ats._lever("cloudflare")
    assert len(result) == 1
    assert result[0].title == "Staff Software Engineer"
    assert result[0].source == "lever/cloudflare"
    assert "Lisbon" in result[0].location
