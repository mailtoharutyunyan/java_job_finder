"""Tests for the Java relevance score."""
from src.models import Job
from src.tagger import relevance_score


def job(title, description=""):
    return Job(title=title, company="Acme", url=f"https://x/{title}",
               source="test", description=description)


def test_strong_java_job_scores_high():
    strong = job("Senior Java Developer",
                 description="Spring Boot, microservices, Kafka, AWS, Kubernetes")
    weak = job("Java Developer", description="basic Java role")
    assert relevance_score(strong) > relevance_score(weak)


def test_non_matching_scores_zero():
    assert relevance_score(job("Product Manager", description="roadmaps")) == 0


def test_java_alone_scores_ten():
    assert relevance_score(job("Java Developer")) == 10
