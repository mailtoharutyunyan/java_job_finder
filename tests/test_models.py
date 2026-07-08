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
