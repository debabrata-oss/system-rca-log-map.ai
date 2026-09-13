import pytest

from rca_log_map.controller.kubectl_commands import KUBECTL_COMMAND_REGISTRY


def test_all_k8s_sources_registered():
    assert {"k8s_events", "k8s_describe_pod", "k8s_pod_logs"} == set(KUBECTL_COMMAND_REGISTRY)


def test_k8s_events_build_args():
    spec = KUBECTL_COMMAND_REGISTRY["k8s_events"]
    assert spec.build_args() == ["get", "events", "-A", "--sort-by=.lastTimestamp"]


def test_k8s_describe_pod_build_args():
    spec = KUBECTL_COMMAND_REGISTRY["k8s_describe_pod"]
    assert spec.build_args(pod="web1", namespace="prod") == ["describe", "pod", "web1", "-n", "prod"]


def test_k8s_describe_pod_rejects_injection():
    spec = KUBECTL_COMMAND_REGISTRY["k8s_describe_pod"]
    with pytest.raises(ValueError):
        spec.build_args(pod="web1; rm -rf /", namespace="prod")
    with pytest.raises(ValueError):
        spec.build_args(pod="web1", namespace="prod; rm -rf /")


def test_k8s_pod_logs_build_args_minimal():
    spec = KUBECTL_COMMAND_REGISTRY["k8s_pod_logs"]
    assert spec.build_args(pod="web1") == ["logs", "web1", "-n", "default", "--tail", "200"]


def test_k8s_pod_logs_build_args_full():
    spec = KUBECTL_COMMAND_REGISTRY["k8s_pod_logs"]
    args = spec.build_args(pod="web1", namespace="prod", container="app", previous=True, lines=50)
    assert args == ["logs", "web1", "-n", "prod", "--tail", "50", "-c", "app", "-p"]


def test_k8s_pod_logs_rejects_bad_container_name():
    spec = KUBECTL_COMMAND_REGISTRY["k8s_pod_logs"]
    with pytest.raises(ValueError):
        spec.build_args(pod="web1", container="app; rm -rf /")


def test_k8s_pod_logs_returns_argv_list_not_shell_string():
    spec = KUBECTL_COMMAND_REGISTRY["k8s_pod_logs"]
    args = spec.build_args(pod="web1")
    assert isinstance(args, list)
    assert all(isinstance(a, str) for a in args)
