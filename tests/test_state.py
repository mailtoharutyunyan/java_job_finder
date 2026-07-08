"""Tests for dedupe state persistence and pruning."""
import json
from datetime import datetime, timedelta, timezone

from src.models import Job
from src.state import SeenStore


def job(n):
    return Job(title=f"Java Dev {n}", company="Acme",
               url=f"https://example.com/job/{n}", source="test")


def same_role_diff_url(n):
    # Same company+title as job(n) but a different apply URL (another board).
    return Job(title=f"Java Dev {n}", company="Acme",
               url=f"https://linkedin.com/jobs/{n}", source="jsearch/linkedin")


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


def test_new_jobs_collapses_cross_source_duplicates(tmp_path):
    store = SeenStore(path=tmp_path / "seen.json")
    jobs = [job(1), same_role_diff_url(1)]  # same role, two boards
    assert len(store.new_jobs(jobs)) == 1


def test_seen_content_blocks_reappearance_from_other_source(tmp_path):
    store = SeenStore(path=tmp_path / "seen.json")
    store.add(job(1))                       # posted from board A
    assert store.has(same_role_diff_url(1))  # same role on board B is not new


def test_save_and_reload(tmp_path):
    path = tmp_path / "seen.json"
    store = SeenStore(path=path)
    store.add(job(1))
    store.save()

    reloaded = SeenStore(path=path)
    assert reloaded.has(job(1))
    assert not reloaded.has(job(2))


def test_prune_removes_old_entries_and_migrates_flat_format(tmp_path):
    path = tmp_path / "seen.json"
    old = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    recent = datetime.now(timezone.utc).isoformat()
    # Old flat {url_key: ts} format is migrated on load.
    path.write_text(json.dumps({"oldkey": old, "newkey": recent}))

    store = SeenStore(path=path)
    store.prune()
    store.save()

    data = json.loads(path.read_text())
    assert "urls" in data and "content" in data
    assert "oldkey" not in data["urls"]
    assert "newkey" in data["urls"]
