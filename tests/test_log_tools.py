from unittest.mock import MagicMock, patch

import pytest

from rca_log_map.config import HostConfig
from rca_log_map.tools import log_tools

HOST_CONFIG = HostConfig(hostname="10.0.0.1", port=22, username="rca-svc", key_path="/fake/key")
RESTRICTED_HOST_CONFIG = HostConfig(
    hostname="10.0.0.1",
    port=22,
    username="rca-svc",
    key_path="/fake/key",
    allowed_sources=["system_messages"],
)


@patch("rca_log_map.audit.record_event")
@patch("rca_log_map.tools.log_tools.SSHController")
def test_unknown_command_rejected_before_any_connection(mock_ssh_controller_cls, mock_record_event):
    with pytest.raises(KeyError):
        log_tools._run("web1", "delete_everything")

    mock_ssh_controller_cls.assert_not_called()
    mock_record_event.assert_called_once()
    assert mock_record_event.call_args.kwargs["error"] is not None


@patch("rca_log_map.audit.record_event")
@patch("rca_log_map.tools.log_tools.SSHController")
@patch("rca_log_map.tools.log_tools.get_host", side_effect=KeyError("unknown host alias 'nope'"))
def test_unknown_host_rejected_before_any_connection(
    mock_get_host, mock_ssh_controller_cls, mock_record_event
):
    with pytest.raises(KeyError):
        log_tools._run("nope", "system_messages")

    mock_ssh_controller_cls.assert_not_called()
    mock_record_event.assert_called_once()


@patch("rca_log_map.audit.record_event")
@patch("rca_log_map.tools.log_tools.SSHController")
@patch("rca_log_map.tools.log_tools.get_host", return_value=RESTRICTED_HOST_CONFIG)
def test_policy_denied_source_rejected_before_any_connection(
    mock_get_host, mock_ssh_controller_cls, mock_record_event
):
    with pytest.raises(PermissionError):
        log_tools._run("web1", "sar_stats")

    mock_ssh_controller_cls.assert_not_called()
    mock_record_event.assert_called_once()


@patch("rca_log_map.audit.record_event")
@patch("rca_log_map.tools.log_tools.SSHController")
@patch("rca_log_map.tools.log_tools.get_host", return_value=HOST_CONFIG)
def test_bad_params_rejected_before_any_connection(mock_get_host, mock_ssh_controller_cls, mock_record_event):
    with pytest.raises(ValueError):
        log_tools._run("web1", "journalctl_service", unit="sshd; reboot", since="1 hour ago")

    mock_ssh_controller_cls.assert_not_called()
    mock_record_event.assert_called_once()


@patch("rca_log_map.tools.log_tools.SSHController")
@patch("rca_log_map.tools.log_tools.get_host", return_value=HOST_CONFIG)
def test_allowed_request_reaches_ssh_controller(mock_get_host, mock_ssh_controller_cls):
    mock_ctl = MagicMock()
    mock_ctl.run.return_value = MagicMock(exit_status=0, stdout="log output", stderr="")
    mock_ssh_controller_cls.return_value.__enter__.return_value = mock_ctl

    result = log_tools._run("web1", "system_messages", lines=50)

    assert result == "log output"
    mock_ctl.run.assert_called_once_with("system_messages", lines=50)
