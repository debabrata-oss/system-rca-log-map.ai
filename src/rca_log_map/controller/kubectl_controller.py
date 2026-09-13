import subprocess

from rca_log_map import audit
from rca_log_map.config import ClusterConfig
from rca_log_map.controller.kubectl_commands import KUBECTL_COMMAND_REGISTRY
from rca_log_map.controller.ssh_controller import CommandResult

COMMAND_TIMEOUT_SECONDS = 30
MAX_OUTPUT_CHARS = 500_000


def _cap(text: str) -> str:
    if len(text) > MAX_OUTPUT_CHARS:
        return text[:MAX_OUTPUT_CHARS] + "\n... [truncated]"
    return text


class KubectlController:
    """Runs kubectl locally against one allowlisted cluster's kubeconfig."""

    def __init__(self, cluster_alias: str, cluster_config: ClusterConfig):
        self.cluster_alias = cluster_alias
        self.cluster_config = cluster_config

    def run(self, command_name: str, **params) -> CommandResult:
        if command_name not in KUBECTL_COMMAND_REGISTRY:
            raise KeyError(f"Unknown command {command_name!r}; not in KUBECTL_COMMAND_REGISTRY")

        spec = KUBECTL_COMMAND_REGISTRY[command_name]
        try:
            args = spec.build_args(**params)
        except ValueError as exc:
            audit.reject(self.cluster_alias, command_name, exc)

        argv = ["kubectl", "--kubeconfig", self.cluster_config.kubeconfig_path]
        if self.cluster_config.context:
            argv += ["--context", self.cluster_config.context]
        argv += args

        proc = subprocess.run(
            argv, capture_output=True, text=True, timeout=COMMAND_TIMEOUT_SECONDS
        )
        result = CommandResult(
            command=" ".join(argv),
            stdout=_cap(proc.stdout),
            stderr=_cap(proc.stderr),
            exit_status=proc.returncode,
        )
        audit.record_event(
            host=self.cluster_alias, command_name=command_name, command=result.command,
            exit_status=proc.returncode,
        )
        return result
