from unittest.mock import MagicMock, patch

import pytest

from rca_log_map.config import ClusterConfig
from rca_log_map.tools import k8s_tools

CLUSTER_CONFIG = ClusterConfig(kubeconfig_path="/fake/kubeconfig")
RESTRICTED_CLUSTER_CONFIG = ClusterConfig(
    kubeconfig_path="/fake/kubeconfig", allowed_sources=["k8s_events"]
)


@patch("rca_log_map.audit.record_event")
@patch("rca_log_map.tools.k8s_tools.KubectlController")
def test_unknown_command_rejected_before_any_call(mock_ctl_cls, mock_record_event):
    with pytest.raises(KeyError):
        k8s_tools._run("prod", "delete_everything")

    mock_ctl_cls.assert_not_called()
    mock_record_event.assert_called_once()


@patch("rca_log_map.audit.record_event")
@patch("rca_log_map.tools.k8s_tools.KubectlController")
@patch("rca_log_map.tools.k8s_tools.get_cluster", side_effect=KeyError("unknown cluster alias 'nope'"))
def test_unknown_cluster_rejected_before_any_call(mock_get_cluster, mock_ctl_cls, mock_record_event):
    with pytest.raises(KeyError):
        k8s_tools._run("nope", "k8s_events")

    mock_ctl_cls.assert_not_called()


@patch("rca_log_map.audit.record_event")
@patch("rca_log_map.tools.k8s_tools.KubectlController")
@patch("rca_log_map.tools.k8s_tools.get_cluster", return_value=RESTRICTED_CLUSTER_CONFIG)
def test_policy_denied_source_rejected_before_any_call(mock_get_cluster, mock_ctl_cls, mock_record_event):
    with pytest.raises(PermissionError):
        k8s_tools._run("prod", "k8s_pod_logs", pod="web1")

    mock_ctl_cls.assert_not_called()


@patch("rca_log_map.audit.record_event")
@patch("rca_log_map.tools.k8s_tools.KubectlController")
@patch("rca_log_map.tools.k8s_tools.get_cluster", return_value=CLUSTER_CONFIG)
def test_bad_params_rejected_before_any_call(mock_get_cluster, mock_ctl_cls, mock_record_event):
    with pytest.raises(ValueError):
        k8s_tools._run("prod", "k8s_describe_pod", pod="web1; rm -rf /")

    mock_ctl_cls.assert_not_called()


@patch("rca_log_map.tools.k8s_tools.KubectlController")
@patch("rca_log_map.tools.k8s_tools.get_cluster", return_value=CLUSTER_CONFIG)
def test_allowed_request_reaches_kubectl_controller(mock_get_cluster, mock_ctl_cls):
    mock_ctl = MagicMock()
    mock_ctl.run.return_value = MagicMock(exit_status=0, stdout="events", stderr="")
    mock_ctl_cls.return_value = mock_ctl

    result = k8s_tools.k8s_events("prod")

    assert result == "events"
    mock_ctl.run.assert_called_once_with("k8s_events")
