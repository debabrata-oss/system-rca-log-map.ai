from unittest.mock import MagicMock, patch

import pytest

from rca_log_map.config import ClusterConfig
from rca_log_map.controller.kubectl_controller import KubectlController

CLUSTER_CONFIG = ClusterConfig(kubeconfig_path="/fake/kubeconfig", context="prod-ctx")


def _mock_proc(stdout="event output\n", stderr="", returncode=0):
    proc = MagicMock()
    proc.stdout = stdout
    proc.stderr = stderr
    proc.returncode = returncode
    return proc


@patch("rca_log_map.audit.record_event")
@patch("rca_log_map.controller.kubectl_controller.subprocess.run")
def test_run_invokes_kubectl_with_argv_list(mock_run, mock_record_event):
    mock_run.return_value = _mock_proc()

    ctl = KubectlController("prod", CLUSTER_CONFIG)
    result = ctl.run("k8s_events")

    (argv,), kwargs = mock_run.call_args
    assert argv == [
        "kubectl", "--kubeconfig", "/fake/kubeconfig", "--context", "prod-ctx",
        "get", "events", "-A", "--sort-by=.lastTimestamp",
    ]
    assert kwargs["capture_output"] is True
    assert kwargs["text"] is True
    assert result.stdout == "event output\n"
    assert result.exit_status == 0

    mock_record_event.assert_called_once()
    assert mock_record_event.call_args.kwargs["host"] == "prod"
    assert mock_record_event.call_args.kwargs["exit_status"] == 0


@patch("rca_log_map.controller.kubectl_controller.subprocess.run")
def test_run_rejects_unknown_command_before_subprocess(mock_run):
    ctl = KubectlController("prod", CLUSTER_CONFIG)
    with pytest.raises(KeyError):
        ctl.run("delete_everything")

    mock_run.assert_not_called()


@patch("rca_log_map.audit.record_event")
@patch("rca_log_map.controller.kubectl_controller.subprocess.run")
def test_run_rejects_bad_params_before_subprocess(mock_run, mock_record_event):
    ctl = KubectlController("prod", CLUSTER_CONFIG)
    with pytest.raises(ValueError):
        ctl.run("k8s_describe_pod", pod="web1; rm -rf /")

    mock_run.assert_not_called()
    mock_record_event.assert_called_once()
    assert mock_record_event.call_args.kwargs["error"] is not None


@patch("rca_log_map.audit.record_event")
@patch("rca_log_map.controller.kubectl_controller.subprocess.run")
def test_run_omits_context_flag_when_not_configured(mock_run, mock_record_event):
    mock_run.return_value = _mock_proc()
    ctl = KubectlController("prod", ClusterConfig(kubeconfig_path="/fake/kubeconfig"))

    ctl.run("k8s_events")

    (argv,), _ = mock_run.call_args
    assert "--context" not in argv
