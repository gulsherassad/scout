"""Tests for the weekly runner's status file and failure rules, with pipeline steps mocked."""
import json
import subprocess

import pytest

import scout.weekly as weekly


def done(stdout="", code=0):
    return subprocess.CompletedProcess([], code, stdout=stdout, stderr="")


@pytest.fixture
def status_file(tmp_path, monkeypatch):
    path = tmp_path / "run_status.json"
    monkeypatch.setattr(weekly, "STATUS", path)
    return path


def fake_steps(monkeypatch, parse_code=0):
    def run(*args):
        if args[0] == "scout.ingest":
            return done("done: 3 fetched, 0 failed\n")
        if args[0] == "scout.parse":
            return done(code=parse_code)
        return done()
    monkeypatch.setattr(weekly, "run", run)


def test_fetched_counts_and_quality_rule():
    assert weekly.fetched_counts("EPL 2026: ...\ndone: 12 fetched, 1 failed\n") == (12, 1)
    assert weekly.quality_ok(0.20, baseline=0.249) and not weekly.quality_ok(0.19, baseline=0.249)


def test_parse_failure_fails_the_run_and_writes_status(monkeypatch, status_file):
    fake_steps(monkeypatch, parse_code=1)
    monkeypatch.setattr(weekly, "recent_recall_at_10", lambda: pytest.fail("must not evaluate"))
    with pytest.raises(SystemExit) as e:
        weekly.main()
    assert e.value.code == 1
    s = json.loads(status_file.read_text())
    assert s["checks_passed"] is False and s["failed_step"] == "parse" and s["matches_fetched"] == 6


def test_quality_alarm_fails_the_run(monkeypatch, status_file):
    fake_steps(monkeypatch)
    monkeypatch.setattr(weekly, "recent_recall_at_10", lambda: (weekly.BASELINE_RECALL_AT_10 - 0.06, 500))
    with pytest.raises(SystemExit) as e:
        weekly.main()
    assert e.value.code == 1
    s = json.loads(status_file.read_text())
    assert s["checks_passed"] is True and s["quality_ok"] is False and s["pool_size"] == 500


def test_healthy_run_passes(monkeypatch, status_file):
    fake_steps(monkeypatch)
    monkeypatch.setattr(weekly, "recent_recall_at_10", lambda: (0.25, 522))
    weekly.main()
    s = json.loads(status_file.read_text())
    assert s["quality_ok"] is True and s["recall_at_10"] == 0.25 and s["failed_step"] is None
