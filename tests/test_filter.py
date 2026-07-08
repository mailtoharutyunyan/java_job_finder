"""Tests for the Java-vs-JavaScript filter."""
from src.filter import matches
from src.models import Job


def job(title, description="", tags=None):
    return Job(title=title, company="Acme", url=f"https://x/{title}",
               source="test", description=description, tags=tags or [])


def test_core_java_passes():
    assert matches(job("Senior Java Developer"))


def test_spring_boot_passes():
    assert matches(job("Backend Engineer", description="We use Spring Boot and PostgreSQL"))


def test_full_stack_java_angular_passes():
    assert matches(job("Full Stack Java Angular Developer"))


def test_java_ai_passes():
    assert matches(job("Machine Learning Engineer", description="Java, LLM, GenAI platform"))


def test_javascript_title_rejected():
    assert not matches(job("Senior JavaScript Developer"))


def test_nodejs_title_rejected():
    assert not matches(job("Node.js Backend Engineer", description="node express mongodb"))


def test_react_title_rejected():
    assert not matches(job("React Frontend Developer"))


def test_javascript_with_real_java_passes():
    # A full-stack role genuinely needing Java should survive the JS guard.
    assert matches(job("Java / JavaScript Full Stack Engineer"))


def test_plain_frontend_rejected():
    assert not matches(job("TypeScript Engineer", description="Vue and TypeScript SPA"))


def test_unrelated_job_rejected():
    assert not matches(job("Python Data Scientist", description="pandas numpy"))


def test_javascript_substring_does_not_trigger_java():
    # "javascript" must not be read as a Java signal.
    assert not matches(job("JavaScript Developer", description="pure javascript role"))


def test_product_manager_with_java_in_description_rejected():
    # Marketplace listings dump a full stack into the description; a PM role
    # must not match just because "java" appears there.
    assert not matches(job("Senior Product Manager",
                           description="Our stack: Java, Spring, Angular, AWS"))


def test_data_scientist_with_java_in_description_rejected():
    assert not matches(job("Senior Data Scientist",
                           description="tools include Java and Spark"))


def test_engineer_title_with_java_in_description_passes():
    # An engineering-role title backs a description-only Java signal.
    assert matches(job("Backend Engineer", description="Java and Spring Boot"))


def test_java_in_tags_passes_generic_title():
    assert matches(job("Software Consultant", tags=["java", "spring"]))
