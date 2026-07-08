"""Tests for Job normalization: cleaning, mojibake repair, dedupe key."""
from src.models import Job


def make(title, url="https://example.com/1"):
    return Job(title=title, company="Acme", url=url, source="test")


def test_mojibake_is_repaired():
    assert make("Analista de Software SÃªnior").title == "Analista de Software Sênior"
    assert make("SÃ£o Paulo").title == "São Paulo"


def test_correct_text_untouched():
    assert make("Sênior Java Developer").title == "Sênior Java Developer"
    assert make("Senior Java Developer").title == "Senior Java Developer"


def test_html_tags_stripped():
    assert make("<b>Java</b> Dev").title == "Java Dev"


def test_dedupe_key_ignores_query_and_trailing_slash():
    a = make("Java", url="https://example.com/job/1/")
    b = make("Java", url="https://example.com/job/1?ref=abc")
    assert a.key == b.key


def test_content_key_ignores_location_suffix():
    # Same role listed per-country should share one content key.
    de = Job(title="Staff Backend Engineer - Alerting | Germany | Remote",
             company="Grafana Labs", url="https://x/de", source="t")
    es = Job(title="Staff Backend Engineer - Alerting | Spain | Remote",
             company="Grafana Labs", url="https://x/es", source="t")
    assert de.content_key == es.content_key


def test_content_key_ignores_parentheticals_and_sr():
    a = Job(title="Sr. Java Developer (Remote)", company="Acme",
            url="https://x/a", source="t")
    b = Job(title="Senior Java Developer", company="Acme",
            url="https://x/b", source="t")
    assert a.content_key == b.content_key
