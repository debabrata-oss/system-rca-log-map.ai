import json
from unittest.mock import patch

import pytest

from rca_log_map.rca.schemas import InvestigationResult, RCAReport
from rca_log_map.webhook import AlertPayload, parse_webhook_payload, run_triggered_investigation

FAKE_RESULT = InvestigationResult(
    report=RCAReport(
        host="web1",
        summary="disk full",
        likely_root_cause="log rotation disabled",
        confidence="high",
        evidence=["/var 100% full"],
        recommended_actions=["enable logrotate"],
        tools_used=["system_messages"],
    ),
    transcript=[],
)


def test_parse_generic_payload():
    alerts = parse_webhook_payload({"host": "web1", "reason": "disk full"})
    assert alerts == [AlertPayload(host="web1", reason="disk full")]


def test_parse_generic_payload_missing_required_field_raises():
    with pytest.raises(ValueError):
        parse_webhook_payload({"reason": "disk full"})


def test_parse_alertmanager_payload_firing_only():
    body = {
        "alerts": [
            {
                "status": "firing",
                "labels": {"instance": "web1", "alertname": "DiskFull"},
                "annotations": {"summary": "disk full on web1"},
            },
            {
                "status": "resolved",
                "labels": {"instance": "web2"},
                "annotations": {"summary": "should be ignored"},
            },
        ]
    }
    alerts = parse_webhook_payload(body)
    assert len(alerts) == 1
    assert alerts[0].host == "web1"
    assert alerts[0].reason == "disk full on web1"


def test_parse_alertmanager_payload_dedupes_by_host():
    body = {
        "alerts": [
            {"status": "firing", "labels": {"instance": "web1"}, "annotations": {"summary": "cpu high"}},
            {"status": "firing", "labels": {"instance": "web1"}, "annotations": {"summary": "mem high"}},
        ]
    }
    alerts = parse_webhook_payload(body)
    assert len(alerts) == 1
    assert "cpu high" in alerts[0].reason
    assert "mem high" in alerts[0].reason


def test_parse_alertmanager_payload_falls_back_to_alertname():
    body = {
        "alerts": [
            {"status": "firing", "labels": {"instance": "web1", "alertname": "DiskFull"}, "annotations": {}},
        ]
    }
    alerts = parse_webhook_payload(body)
    assert alerts[0].reason == "DiskFull"


def test_parse_alertmanager_payload_skips_alert_without_host():
    body = {"alerts": [{"status": "firing", "labels": {}, "annotations": {"summary": "x"}}]}
    assert parse_webhook_payload(body) == []


@patch("rca_log_map.webhook.investigate", return_value=FAKE_RESULT)
def test_run_triggered_investigation_writes_success_report(mock_investigate, tmp_path, monkeypatch):
    monkeypatch.setenv("RCA_REPORTS_DIR", str(tmp_path))
    alert = AlertPayload(host="web1", reason="disk full")

    run_triggered_investigation(alert)

    files = list(tmp_path.glob("*_web1.json"))
    assert len(files) == 1
    record = json.loads(files[0].read_text())
    assert record["status"] == "ok"
    assert record["result"]["report"]["likely_root_cause"] == "log rotation disabled"
    assert record["alert"]["host"] == "web1"


@patch("rca_log_map.webhook.investigate", side_effect=KeyError("unknown host alias 'web1'"))
def test_run_triggered_investigation_writes_error_report_not_silently_dropped(
    mock_investigate, tmp_path, monkeypatch
):
    monkeypatch.setenv("RCA_REPORTS_DIR", str(tmp_path))
    alert = AlertPayload(host="web1", reason="disk full")

    run_triggered_investigation(alert)

    files = list(tmp_path.glob("*_web1.json"))
    assert len(files) == 1
    record = json.loads(files[0].read_text())
    assert record["status"] == "error"
    assert "unknown host" in record["error"]


@patch("rca_log_map.webhook.investigate", side_effect=KeyError("unknown host alias"))
def test_malicious_host_cannot_escape_reports_dir(mock_investigate, tmp_path, monkeypatch):
    monkeypatch.setenv("RCA_REPORTS_DIR", str(tmp_path))
    alert = AlertPayload(host="../../../../tmp/escaped_pwn", reason="x")

    run_triggered_investigation(alert)

    written = list(tmp_path.rglob("*.json"))
    assert len(written) == 1
    assert written[0].resolve().is_relative_to(tmp_path.resolve())
