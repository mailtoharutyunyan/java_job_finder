"""Tests for dedupe state persistence and pruning."""
import json
from datetime import datetime, timedelta, timezone

from src.models import Job
from src.state import SeenStore


def job(n):
    return Job(title=f"Java Dev {n}", company="Acme",
               url=f"https://example.com/job/{n}", source="test")


def test_new_jobs_excludes_seen(tmp_path):
    store = SeenStore(path=tmp_path / "seen.json")
    jobs = [job(1), job(2), job(3)]
    assert len(store.new_jobs(jobs)) == 3
    store.add(jobs[0])
    assert len(store.new_jobs(jobs)) == 2


def test_new_jobs_dedupes_within_batch(tmp_path):
    store = SeenStore(path=tmp_path / "seen.json")
    jobs = [job(1), job(1), job(2)]  # duplicate url in same batch
    assert len(store.new_jobs(jobs)) == 2


def test_save_and_reload(tmp_path):
    path = tmp_path / "seen.json"
    store = SeenStore(path=path)
    store.add(job(1))
    store.save()

    reloaded = SeenStore(path=path)
    assert reloaded.has(job(1))
    assert not reloaded.has(job(2))


def test_prune_removes_old_entries(tmp_path):
    path = tmp_path / "seen.json"
    old = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    recent = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps({"oldkey": old, "newkey": recent}))

    store = SeenStore(path=path)
    store.prune()
    store.save()

    data = json.loads(path.read_text())
    assert "oldkey" not in data
    assert "newkey" in data
