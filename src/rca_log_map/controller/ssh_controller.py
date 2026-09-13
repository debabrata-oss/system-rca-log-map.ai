import logging
from dataclasses import dataclass

import paramiko

from rca_log_map.config import HostConfig
from rca_log_map.controller.commands import COMMAND_REGISTRY

logger = logging.getLogger(__name__)

CONNECT_TIMEOUT_SECONDS = 10
COMMAND_TIMEOUT_SECONDS = 30
MAX_OUTPUT_BYTES = 500_000


@dataclass(frozen=True)
class CommandResult:
    command: str
    stdout: str
    stderr: str
    exit_status: int


def _read_capped(stream) -> str:
    data = stream.read(MAX_OUTPUT_BYTES + 1)
    text = data.decode("utf-8", errors="replace")
    if len(data) > MAX_OUTPUT_BYTES:
        text = text[:MAX_OUTPUT_BYTES] + "\n... [truncated]"
    return text


class SSHController:
    """Connects to a single allowlisted host and runs only registered, validated commands."""

    def __init__(self, host_alias: str, host_config: HostConfig):
        self.host_alias = host_alias
        self.host_config = host_config
        self._client: paramiko.SSHClient | None = None

    def __enter__(self) -> "SSHController":
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.RejectPolicy())
        client.connect(
            hostname=self.host_config.hostname,
            port=self.host_config.port,
            username=self.host_config.username,
            key_filename=self.host_config.key_path,
            timeout=CONNECT_TIMEOUT_SECONDS,
            allow_agent=False,
            look_for_keys=False,
        )
        self._client = client
        return self

    def __exit__(self, *exc_info) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def run(self, command_name: str, **params) -> CommandResult:
        if self._client is None:
            raise RuntimeError("SSHController must be used as a context manager")
        if command_name not in COMMAND_REGISTRY:
            raise KeyError(f"Unknown command {command_name!r}; not in COMMAND_REGISTRY")

        spec = COMMAND_REGISTRY[command_name]
        rendered = spec.render(**params)

        logger.info(
            "executing command_name=%s host=%s rendered=%r",
            command_name,
            self.host_alias,
            rendered,
        )
        _, stdout, stderr = self._client.exec_command(rendered, timeout=COMMAND_TIMEOUT_SECONDS)
        exit_status = stdout.channel.recv_exit_status()
        result = CommandResult(
            command=rendered,
            stdout=_read_capped(stdout),
            stderr=_read_capped(stderr),
            exit_status=exit_status,
        )
        logger.info(
            "completed command_name=%s host=%s exit_status=%d",
            command_name,
            self.host_alias,
            exit_status,
        )
        return result
