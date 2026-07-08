"""Tests for The Muse response parsing (no network)."""
from src.fetchers import themuse
from src.filter import matches

SAMPLE = {
    "results": [
        {
            "name": "Senior Java Engineer",
            "company": {"name": "Acme Corp"},
            "locations": [{"name": "Berlin, Germany"}, {"name": "Flexible / Remote"}],
            "levels": [{"name": "Senior Level"}],
            "categories": [{"name": "Software Engineering"}],
            "contents": "<p>Build services with <b>Java</b> and Spring Boot.</p>",
            "publication_date": "2026-07-08T10:00:00Z",
            "refs": {"landing_page": "https://www.themuse.com/jobs/acme/senior-java"},
        },
        {
            # No landing page → skipped.
            "name": "Java Developer",
            "company": {"name": "NoLink"},
            "refs": {},
        },
    ]
}


def test_parse_basic_fields():
    jobs = themuse._parse_page(SAMPLE)
    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Senior Java Engineer"
    assert job.company == "Acme Corp"
    assert job.source == "themuse"
    assert "Berlin" in job.location
    assert job.url.endswith("senior-java")
    assert matches(job)  # HTML stripped, Java detected


def test_parse_empty():
    assert themuse._parse_page({"results": []}) == []
    assert themuse._parse_page({}) == []
