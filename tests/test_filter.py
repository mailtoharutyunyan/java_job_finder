"""Tests for the Java-vs-JavaScript filter."""
from src.filter import filter_java, is_remote_or_relocation, matches
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


def test_python_title_with_polluted_java_tag_rejected():
    # RemoteOK sometimes tags a Python role with "java"; the title must win.
    assert not matches(job("Python Developer Brazil", tags=["java", "python"]))


def test_go_developer_rejected():
    assert not matches(job("Golang Developer", tags=["java", "golang"]))


def test_frontend_only_rejected():
    assert not matches(job("Front End Full Stack Developer", tags=["java"]))


def test_dotnet_rejected():
    assert not matches(job("Senior .NET Engineer", description="C# and Java interop"))


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


# --- remote / worldwide / relocation location filter ---

def loc_job(title="Java Developer", location="", tags=None, description=""):
    return Job(title=title, company="Acme", url=f"https://x/{title}{location}",
               source="test", location=location, tags=tags or [], description=description)


def test_remote_location_passes():
    assert is_remote_or_relocation(loc_job(location="Remote, Worldwide"))


def test_anywhere_tag_passes():
    assert is_remote_or_relocation(loc_job(tags=["anywhere"]))


def test_relocation_in_description_passes():
    assert is_remote_or_relocation(
        loc_job(location="Berlin", description="On-site with full relocation package"))


def test_visa_sponsorship_passes():
    assert is_remote_or_relocation(
        loc_job(location="Amsterdam", description="We offer visa sponsorship"))


def test_plain_onsite_rejected():
    assert not is_remote_or_relocation(
        loc_job(location="Munich", description="On-site role in our Munich office"))


def test_filter_java_requires_java_and_location():
    jobs = [
        loc_job("Senior Java Developer", location="Remote"),          # java + remote → keep
        loc_job("Senior Java Developer", location="Munich office"),   # java, on-site → drop
        loc_job("Python Developer", location="Remote"),               # remote, not java → drop
    ]
    kept = filter_java(jobs)
    assert len(kept) == 1
    assert kept[0].location == "Remote"
