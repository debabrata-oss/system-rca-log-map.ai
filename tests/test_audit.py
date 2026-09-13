import json

import pytest

from rca_log_map import audit


@pytest.fixture(autouse=True)
def _reset_actor():
    audit.set_actor("unknown")
    yield
    audit.set_actor("unknown")


def test_default_actor_is_unknown():
    assert audit.current_actor() == "unknown"


def test_set_and_get_actor():
    audit.set_actor("alice")
    assert audit.current_actor() == "alice"


def test_record_event_writes_jsonl(tmp_path, monkeypatch):
    log_path = tmp_path / "audit.log"
    monkeypatch.setenv("RCA_AUDIT_LOG_PATH", str(log_path))
    audit.set_actor("alice")

    audit.record_event(
        host="web1", command_name="system_messages",
        command="tail -n 200 /var/log/messages", exit_status=0,
    )

    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["actor"] == "alice"
    assert entry["host"] == "web1"
    assert entry["command_name"] == "system_messages"
    assert entry["exit_status"] == 0
    assert entry["error"] is None
    assert "timestamp" in entry


def test_record_event_appends_multiple_entries(tmp_path, monkeypatch):
    log_path = tmp_path / "audit.log"
    monkeypatch.setenv("RCA_AUDIT_LOG_PATH", str(log_path))

    audit.record_event(host="web1", command_name="a", command="a", exit_status=0)
    audit.record_event(host="web1", command_name="b", command=None, exit_status=None, error="denied")

    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[1])["error"] == "denied"


def test_record_event_creates_parent_dirs(tmp_path, monkeypatch):
    log_path = tmp_path / "nested" / "dir" / "audit.log"
    monkeypatch.setenv("RCA_AUDIT_LOG_PATH", str(log_path))

    audit.record_event(host="web1", command_name="a", command="a", exit_status=0)

    assert log_path.exists()
