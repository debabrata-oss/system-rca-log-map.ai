from collections.abc import Callable
from dataclasses import dataclass

from rca_log_map.controller.validation import validate_k8s_name, validate_lines


@dataclass(frozen=True)
class KubectlCommandSpec:
    description: str
    build_args: Callable[..., list[str]]


def _k8s_events() -> list[str]:
    return ["get", "events", "-A", "--sort-by=.lastTimestamp"]


def _k8s_describe_pod(pod: str, namespace: str = "default") -> list[str]:
    pod = validate_k8s_name(pod, "pod")
    namespace = validate_k8s_name(namespace, "namespace")
    return ["describe", "pod", pod, "-n", namespace]


def _k8s_pod_logs(
    pod: str,
    namespace: str = "default",
    container: str | None = None,
    previous: bool = False,
    lines: int = 200,
) -> list[str]:
    pod = validate_k8s_name(pod, "pod")
    namespace = validate_k8s_name(namespace, "namespace")
    lines = validate_lines(lines)
    args = ["logs", pod, "-n", namespace, "--tail", str(lines)]
    if container is not None:
        args += ["-c", validate_k8s_name(container, "container")]
    if previous:
        args.append("-p")
    return args


KUBECTL_COMMAND_REGISTRY: dict[str, KubectlCommandSpec] = {
    "k8s_events": KubectlCommandSpec(
        description="Cluster-wide recent failures (kubectl get events -A --sort-by=.lastTimestamp).",
        build_args=_k8s_events,
    ),
    "k8s_describe_pod": KubectlCommandSpec(
        description="Scheduling, image pull, probe, and OOM reasons (kubectl describe pod).",
        build_args=_k8s_describe_pod,
    ),
    "k8s_pod_logs": KubectlCommandSpec(
        description="App container logs; set previous=True for a crashed instance's prior logs.",
        build_args=_k8s_pod_logs,
    ),
}
