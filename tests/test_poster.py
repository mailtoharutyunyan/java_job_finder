"""Tests for message formatting (no network)."""
from src.models import Job
from src.poster import DIGEST_SIZE, format_digest, format_message


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


def test_digest_lists_jobs_as_links():
    jobs = [Job(title=f"Java Developer {n}", company=f"Co{n}",
                url=f"https://example.com/{n}", source="test", location="Remote")
            for n in range(1, 4)]
    msg = format_digest(jobs)
    assert "3 new" in msg
    for n in range(1, 4):
        assert f'<a href="https://example.com/{n}">Java Developer {n}</a>' in msg


def test_digest_shows_hashtags():
    j = Job(title="Senior Java Developer", company="Acme", url="https://x/1",
            source="remotefirstjobs", location="Remote",
            description="Spring Boot, AWS, Kafka")
    msg = format_digest([j])
    assert "#java" in msg
    assert "#spring" in msg
    assert "#remotefirstjobs" in msg


def test_digest_groups_by_company():
    jobs = [
        Job(title="Java Dev A", company="Acme", url="https://x/a", source="test"),
        Job(title="Java Dev B", company="Acme", url="https://x/b", source="test"),
        Job(title="Java Dev C", company="Beta", url="https://x/c", source="test"),
    ]
    msg = format_digest(jobs)
    assert msg.count("<b>Acme</b>") == 1
    assert msg.count("<b>Beta</b>") == 1


def test_digest_shows_source_website():
    j = Job(title="Java Developer", company="Acme", url="https://x/1",
            source="weworkremotely", location="Remote")
    assert "🌐 WeWorkRemotely" in format_digest([j])
    ats = Job(title="Java Developer", company="GitLab",
              url="https://x/2", source="greenhouse/gitlab", location="Remote")
    assert "🌐 Greenhouse" in format_digest([ats])


def test_digest_caps_at_size():
    jobs = [Job(title=f"Java Dev {n}", company=f"Co{n}", url=f"https://x/{n}",
                source="test") for n in range(20)]
    msg = format_digest(jobs)
    assert ">Java Dev 0<" in msg
    assert f">Java Dev {DIGEST_SIZE}<" not in msg  # 11th job (index 10) excluded


def test_html_is_sanitized():
    # Job._clean strips HTML tags; format_message then escapes stray entities.
    j = Job(title="Java <script> Dev & Co", company="A<b>",
            url="https://example.com/4", source="test")
    msg = format_message(j)
    assert "<script>" not in msg          # tag removed by _clean
    assert "&amp;" in msg                  # bare & escaped for HTML parse_mode
    assert "Java Dev" in msg
