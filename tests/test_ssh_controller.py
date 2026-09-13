from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from rca_log_map.config import HostConfig
from rca_log_map.controller.ssh_controller import SSHController

HOST_CONFIG = HostConfig(
    hostname="10.0.0.1", port=22, username="rca-svc", key_path="/fake/key"
)


def _mock_client(stdout_bytes: bytes = b"log line\n", stderr_bytes: bytes = b"", exit_status: int = 0):
    client = MagicMock()
    stdout = BytesIO(stdout_bytes)
    stderr = BytesIO(stderr_bytes)
    stdout.channel = MagicMock()
    stdout.channel.recv_exit_status.return_value = exit_status
    client.exec_command.return_value = (MagicMock(), stdout, stderr)
    return client


@patch("rca_log_map.audit.record_event")
@patch("rca_log_map.controller.ssh_controller.paramiko.SSHClient")
def test_run_calls_exec_command_with_rendered_string(mock_ssh_client_cls, mock_record_event):
    mock_ssh_client_cls.return_value = _mock_client()

    with SSHController("web1", HOST_CONFIG) as ctl:
        result = ctl.run("journalctl_recent_errors", lines=50)

    mock_ssh_client_cls.return_value.exec_command.assert_called_once()
    (called_command,), _ = mock_ssh_client_cls.return_value.exec_command.call_args
    assert called_command == "journalctl -xe -n 50 --no-pager"
    assert result.stdout == "log line\n"
    assert result.exit_status == 0

    mock_record_event.assert_called_once_with(
        host="web1", command_name="journalctl_recent_errors",
        command="journalctl -xe -n 50 --no-pager", exit_status=0,
    )


@patch("rca_log_map.controller.ssh_controller.paramiko.SSHClient")
def test_run_rejects_unknown_command_before_exec(mock_ssh_client_cls):
    mock_ssh_client_cls.return_value = _mock_client()

    with SSHController("web1", HOST_CONFIG) as ctl:
        with pytest.raises(KeyError):
            ctl.run("delete_everything")

    mock_ssh_client_cls.return_value.exec_command.assert_not_called()


@patch("rca_log_map.audit.record_event")
@patch("rca_log_map.controller.ssh_controller.paramiko.SSHClient")
def test_run_rejects_bad_params_before_exec(mock_ssh_client_cls, mock_record_event):
    mock_ssh_client_cls.return_value = _mock_client()

    with SSHController("web1", HOST_CONFIG) as ctl:
        with pytest.raises(ValueError):
            ctl.run("journalctl_service", unit="sshd; reboot", since="1 hour ago")

    mock_ssh_client_cls.return_value.exec_command.assert_not_called()
    mock_record_event.assert_called_once()
    assert mock_record_event.call_args.kwargs["error"] is not None


@patch("rca_log_map.controller.ssh_controller.paramiko.SSHClient")
def test_connect_uses_reject_policy_and_no_agent(mock_ssh_client_cls):
    mock_ssh_client_cls.return_value = _mock_client()

    with SSHController("web1", HOST_CONFIG):
        pass

    client = mock_ssh_client_cls.return_value
    client.set_missing_host_key_policy.assert_called_once()
    _, connect_kwargs = client.connect.call_args
    assert connect_kwargs["allow_agent"] is False
    assert connect_kwargs["look_for_keys"] is False
    assert connect_kwargs["key_filename"] == "/fake/key"
