import copy
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from rca_log_map.rca.agent import investigate
from rca_log_map.rca.schemas import InvestigationResult

REPORT_INPUT = {
    "summary": "sshd crashed",
    "likely_root_cause": "OOM kill",
    "confidence": "high",
    "evidence": ["oom-killer invoked on sshd"],
    "recommended_actions": ["increase memory limit"],
}


def _tool_use(id_: str, name: str, input_: dict) -> SimpleNamespace:
    return SimpleNamespace(type="tool_use", id=id_, name=name, input=input_)


def _response(blocks: list) -> SimpleNamespace:
    return SimpleNamespace(content=blocks)


def _scripted_client(responses: list, seen_calls: list) -> MagicMock:
    client = MagicMock()
    remaining = list(responses)

    def fake_create(**kwargs):
        seen_calls.append(copy.deepcopy({"messages": kwargs["messages"], "tool_choice": kwargs["tool_choice"]}))
        return remaining.pop(0)

    client.messages.create.side_effect = fake_create
    return client


@patch("rca_log_map.rca.agent.get_host", return_value=None)
@patch("rca_log_map.rca.agent.anthropic.Anthropic")
def test_investigate_dispatches_tool_and_returns_report(mock_anthropic_cls, mock_get_host):
    seen_calls: list = []
    responses = [
        _response([_tool_use("t1", "journalctl_service", {"unit": "sshd"})]),
        _response([_tool_use("t2", "submit_rca_report", REPORT_INPUT)]),
    ]
    mock_anthropic_cls.return_value = _scripted_client(responses, seen_calls)

    with patch.dict(
        "rca_log_map.rca.agent.LOG_TOOL_DISPATCH",
        {"journalctl_service": MagicMock(return_value="fake log output")},
    ):
        result = investigate("web1", "what broke?", max_iterations=6)

    assert isinstance(result, InvestigationResult)
    assert result.report.host == "web1"
    assert result.report.likely_root_cause == "OOM kill"
    assert result.report.tools_used == ["journalctl_service"]
    assert [e.type for e in result.transcript] == ["tool_call", "tool_result"]
    assert result.transcript[1].output == "fake log output"

    second_call_messages = seen_calls[1]["messages"]
    tool_result_message = second_call_messages[2]
    assert tool_result_message["role"] == "user"
    assert tool_result_message["content"][0]["content"] == "fake log output"
    assert tool_result_message["content"][0]["tool_use_id"] == "t1"


@patch("rca_log_map.rca.agent.get_host", return_value=None)
@patch("rca_log_map.rca.agent.anthropic.Anthropic")
def test_tool_error_is_fed_back_not_raised(mock_anthropic_cls, mock_get_host):
    seen_calls: list = []
    responses = [
        _response([_tool_use("t1", "journalctl_service", {"unit": "sshd"})]),
        _response([_tool_use("t2", "submit_rca_report", REPORT_INPUT)]),
    ]
    mock_anthropic_cls.return_value = _scripted_client(responses, seen_calls)

    def raise_value_error(**kwargs):
        raise ValueError("invalid systemd unit name")

    with patch.dict(
        "rca_log_map.rca.agent.LOG_TOOL_DISPATCH", {"journalctl_service": raise_value_error}
    ):
        result = investigate("web1", "what broke?", max_iterations=6)

    assert isinstance(result, InvestigationResult)
    assert "Error:" in result.transcript[1].output
    tool_result_content = seen_calls[1]["messages"][2]["content"][0]["content"]
    assert "Error:" in tool_result_content


@patch("rca_log_map.rca.agent.get_host", return_value=None)
@patch("rca_log_map.rca.agent.anthropic.Anthropic")
def test_forced_final_turn_uses_submit_tool_choice(mock_anthropic_cls, mock_get_host):
    seen_calls: list = []
    responses = [
        _response([_tool_use("t1", "journalctl_service", {"unit": "sshd"})]),
        _response([_tool_use("t2", "submit_rca_report", REPORT_INPUT)]),
    ]
    mock_anthropic_cls.return_value = _scripted_client(responses, seen_calls)

    with patch.dict(
        "rca_log_map.rca.agent.LOG_TOOL_DISPATCH",
        {"journalctl_service": MagicMock(return_value="fake log output")},
    ):
        result = investigate("web1", "what broke?", max_iterations=2)

    assert isinstance(result, InvestigationResult)
    assert seen_calls[0]["tool_choice"] == {"type": "auto"}
    assert seen_calls[1]["tool_choice"] == {"type": "tool", "name": "submit_rca_report"}


@patch("rca_log_map.rca.agent.get_host", side_effect=KeyError("unknown host alias 'nope'"))
@patch("rca_log_map.rca.agent.anthropic.Anthropic")
def test_unknown_host_fails_before_any_api_call(mock_anthropic_cls, mock_get_host):
    with pytest.raises(KeyError):
        investigate("nope", "what broke?")

    mock_anthropic_cls.assert_not_called()
