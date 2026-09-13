from rca_log_map import audit
from rca_log_map.config import get_cluster
from rca_log_map.controller.kubectl_commands import KUBECTL_COMMAND_REGISTRY
from rca_log_map.controller.kubectl_controller import KubectlController


def _run(cluster: str, command_name: str, **params) -> str:
    if command_name not in KUBECTL_COMMAND_REGISTRY:
        error = KeyError(f"Unknown command {command_name!r}; not in KUBECTL_COMMAND_REGISTRY")
        audit.reject(cluster, command_name, error)

    try:
        cluster_config = get_cluster(cluster)
    except (KeyError, FileNotFoundError) as exc:
        audit.reject(cluster, command_name, exc)

    if not cluster_config.is_source_allowed(command_name):
        audit.reject(
            cluster,
            command_name,
            PermissionError(f"{command_name!r} is not permitted on cluster {cluster!r}"),
        )

    # Validate/build args before ever invoking subprocess, same fail-fast principle as log_tools.
    try:
        KUBECTL_COMMAND_REGISTRY[command_name].build_args(**params)
    except ValueError as exc:
        audit.reject(cluster, command_name, exc)

    result = KubectlController(cluster, cluster_config).run(command_name, **params)
    if result.exit_status != 0:
        return (
            f"[{command_name} on cluster {cluster} exited {result.exit_status}]\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result.stdout


def k8s_events(cluster: str) -> str:
    """Cluster-wide recent failures via kubectl get events -A --sort-by=.lastTimestamp."""
    return _run(cluster, "k8s_events")


def k8s_describe_pod(cluster: str, pod: str, namespace: str = "default") -> str:
    """Scheduling, image pull, probe, and OOM reasons via kubectl describe pod."""
    return _run(cluster, "k8s_describe_pod", pod=pod, namespace=namespace)


def k8s_pod_logs(
    cluster: str,
    pod: str,
    namespace: str = "default",
    container: str | None = None,
    previous: bool = False,
    lines: int = 200,
) -> str:
    """App container logs via kubectl logs; set previous=True for a crashed instance's prior logs."""
    kwargs = {"pod": pod, "namespace": namespace, "lines": lines, "previous": previous}
    if container is not None:
        kwargs["container"] = container
    return _run(cluster, "k8s_pod_logs", **kwargs)


ALL_K8S_TOOLS = (
    k8s_events,
    k8s_describe_pod,
    k8s_pod_logs,
)
