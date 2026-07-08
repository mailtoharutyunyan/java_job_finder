"""Tests for message formatting (no network)."""
from src.models import Job
from src.poster import format_message


def test_message_contains_core_fields():
    j = Job(title="Senior Java Developer", company="Acme Corp",
            url="https://example.com/job/1", source="test",
            location="Remote (EU)", salary="€70k-90k",
            description="Spring Boot AWS Angular")
    msg = format_message(j)
    assert "Senior Java Developer" in msg
    assert "Acme Corp" in msg
    assert "Remote (EU)" in msg
    assert "€70k-90k" in msg
    assert "https://example.com/job/1" in msg
    assert "#java" in msg


def test_profile_match_badge_present():
    j = Job(title="Java Developer", company="Acme",
            url="https://example.com/2", source="test",
            description="AWS Angular AI")
    assert "PROFILE MATCH" in format_message(j)


def test_no_badge_without_profile_skills():
    j = Job(title="Java Developer", company="Acme",
            url="https://example.com/3", source="test",
            description="Oracle DB on-prem")
    assert "PROFILE MATCH" not in format_message(j)


def test_html_is_sanitized():
    # Job._clean strips HTML tags; format_message then escapes stray entities.
    j = Job(title="Java <script> Dev & Co", company="A<b>",
            url="https://example.com/4", source="test")
    msg = format_message(j)
    assert "<script>" not in msg          # tag removed by _clean
    assert "&amp;" in msg                  # bare & escaped for HTML parse_mode
    assert "Java Dev" in msg
