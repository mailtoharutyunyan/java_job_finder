"""Tests for skill hashtag detection and profile matching."""
from src.models import Job
from src.tagger import hashtags, is_profile_match, source_hashtag


def job(title, description="", tags=None):
    return Job(title=title, company="Acme", url=f"https://x/{title}",
               source="test", description=description, tags=tags or [])


def test_detects_core_skills():
    tags = hashtags(job("Java Developer", description="Spring Boot, AWS, Kafka, Docker"))
    assert "#java" in tags
    assert "#spring" in tags
    assert "#aws" in tags
    assert "#kafka" in tags
    assert "#docker" in tags


def test_detects_angular_fullstack():
    tags = hashtags(job("Full Stack Java Angular Developer"))
    assert "#fullstack" in tags
    assert "#angular" in tags


def test_detects_ai():
    tags = hashtags(job("Java Engineer", description="building LLM and GenAI systems"))
    assert "#ai" in tags


def test_profile_match_true_for_aws():
    assert is_profile_match(job("Java Developer", description="AWS cloud platform"))


def test_profile_match_false_without_target_skills():
    assert not is_profile_match(job("Java Developer", description="on-prem Oracle DB"))


def test_source_hashtag_jsearch_publisher():
    j = job("Java Dev")
    j.source = "jsearch/linkedin"
    assert source_hashtag(j) == "#linkedin"


def test_source_hashtag_plain_source():
    j = job("Java Dev")
    j.source = "remotive"
    assert source_hashtag(j) == "#remotive"


def test_source_hashtag_strips_special_chars():
    j = job("Java Dev")
    j.source = "jsearch/Talent.com"
    assert source_hashtag(j) == "#talentcom"


def test_hashtags_are_unique_and_ordered():
    tags = hashtags(job("Senior Java Developer", description="java java spring"))
    assert tags == list(dict.fromkeys(tags))
    assert tags[0] == "#java"
