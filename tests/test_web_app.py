from unittest.mock import patch

from fastapi.testclient import TestClient

from rca_log_map.config import HostConfig
from rca_log_map.rca.schemas import InvestigationResult, RCAReport, TranscriptEvent
from rca_log_map.web.app import app
from rca_log_map.web.auth import API_KEY_ENV_VAR

client = TestClient(app)

FAKE_HOSTS = {"web1": HostConfig(hostname="10.0.0.1", port=22, username="rca-svc", key_path="/fake/key")}

FAKE_RESULT = InvestigationResult(
    report=RCAReport(
        host="web1",
        summary="sshd crashed",
        likely_root_cause="OOM kill",
        confidence="high",
        evidence=["oom-killer invoked"],
        recommended_actions=["increase memory"],
        tools_used=["journalctl_service"],
    ),
    transcript=[
        TranscriptEvent(type="tool_call", name="journalctl_service", input={"unit": "sshd"}),
        TranscriptEvent(type="tool_result", name="journalctl_service", output="fake log output"),
    ],
)


def test_healthz_requires_no_api_key():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_hosts_requires_api_key(monkeypatch):
    monkeypatch.setenv(API_KEY_ENV_VAR, "secret")
    response = client.get("/api/hosts")
    assert response.status_code == 401


def test_hosts_rejects_wrong_key(monkeypatch):
    monkeypatch.setenv(API_KEY_ENV_VAR, "secret")
    response = client.get("/api/hosts", headers={"X-API-Key": "wrong"})
    assert response.status_code == 401


def test_hosts_returns_configured_aliases(monkeypatch):
    monkeypatch.setenv(API_KEY_ENV_VAR, "secret")
    with patch("rca_log_map.web.app.load_hosts", return_value=FAKE_HOSTS):
        response = client.get("/api/hosts", headers={"X-API-Key": "secret"})
    assert response.status_code == 200
    assert response.json() == [{"alias": "web1", "hostname": "10.0.0.1"}]


def test_hosts_returns_400_not_500_when_config_missing(monkeypatch):
    monkeypatch.setenv(API_KEY_ENV_VAR, "secret")

    def raise_missing_config():
        raise FileNotFoundError("Host inventory not found at config/hosts.yaml")

    with patch("rca_log_map.web.app.load_hosts", side_effect=raise_missing_config):
        response = client.get("/api/hosts", headers={"X-API-Key": "secret"})
    assert response.status_code == 400
    assert "Host inventory not found" in response.json()["detail"]


def test_investigate_returns_report_and_transcript(monkeypatch):
    monkeypatch.setenv(API_KEY_ENV_VAR, "secret")
    with patch("rca_log_map.web.app.run_investigation", return_value=FAKE_RESULT):
        response = client.post(
            "/api/investigate",
            headers={"X-API-Key": "secret"},
            json={"host": "web1", "question": "what broke?"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["report"]["likely_root_cause"] == "OOM kill"
    assert body["transcript"][1]["output"] == "fake log output"


def test_investigate_maps_known_errors_to_400_not_500(monkeypatch):
    monkeypatch.setenv(API_KEY_ENV_VAR, "secret")

    def raise_unknown_host(*args, **kwargs):
        raise KeyError("unknown host alias 'nope'")

    with patch("rca_log_map.web.app.run_investigation", side_effect=raise_unknown_host):
        response = client.post(
            "/api/investigate",
            headers={"X-API-Key": "secret"},
            json={"host": "nope", "question": "what broke?"},
        )
    assert response.status_code == 400
    assert "unknown host" in response.json()["detail"]


def test_require_api_key_raises_when_env_var_unset(monkeypatch):
    monkeypatch.delenv(API_KEY_ENV_VAR, raising=False)
    from rca_log_map.web.auth import require_api_key

    try:
        require_api_key(x_api_key="anything")
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert API_KEY_ENV_VAR in str(exc)


def test_webhook_requires_api_key(monkeypatch):
    monkeypatch.setenv(API_KEY_ENV_VAR, "secret")
    response = client.post("/webhook/alert", json={"host": "web1", "reason": "x"})
    assert response.status_code == 401


def test_webhook_accepts_query_param_key(monkeypatch):
    monkeypatch.setenv(API_KEY_ENV_VAR, "secret")
    with patch("rca_log_map.web.app.run_triggered_investigation"):
        response = client.post(
            "/webhook/alert?api_key=secret", json={"host": "web1", "reason": "x"}
        )
    assert response.status_code == 202


def test_webhook_generic_payload_schedules_one_investigation(monkeypatch):
    monkeypatch.setenv(API_KEY_ENV_VAR, "secret")
    with patch("rca_log_map.web.app.run_triggered_investigation") as mock_run:
        response = client.post(
            "/webhook/alert",
            headers={"X-API-Key": "secret"},
            json={"host": "web1", "reason": "disk full"},
        )
    assert response.status_code == 202
    assert response.json() == {"accepted": 1}
    mock_run.assert_called_once()
    assert mock_run.call_args.args[0].host == "web1"


def test_webhook_alertmanager_payload_schedules_one_per_host(monkeypatch):
    monkeypatch.setenv(API_KEY_ENV_VAR, "secret")
    body = {
        "alerts": [
            {"status": "firing", "labels": {"instance": "web1"}, "annotations": {"summary": "a"}},
            {"status": "firing", "labels": {"instance": "web2"}, "annotations": {"summary": "b"}},
        ]
    }
    with patch("rca_log_map.web.app.run_triggered_investigation") as mock_run:
        response = client.post("/webhook/alert", headers={"X-API-Key": "secret"}, json=body)
    assert response.status_code == 202
    assert response.json() == {"accepted": 2}
    assert mock_run.call_count == 2


def test_webhook_invalid_payload_returns_400_not_500(monkeypatch):
    monkeypatch.setenv(API_KEY_ENV_VAR, "secret")
    response = client.post(
        "/webhook/alert", headers={"X-API-Key": "secret"}, json={"reason": "missing host"}
    )
    assert response.status_code == 400
