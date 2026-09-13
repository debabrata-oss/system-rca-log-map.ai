import json
import logging
import os
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_actor_var: ContextVar[str] = ContextVar("rca_actor", default="unknown")

DEFAULT_AUDIT_LOG_PATH = "logs/audit.log"


def set_actor(actor: str) -> None:
    _actor_var.set(actor)


def current_actor() -> str:
    return _actor_var.get()


def record_event(
    host: str,
    command_name: str,
    command: str | None,
    exit_status: int | None,
    error: str | None = None,
) -> None:
    entry = {
        "timestamp": datetime.now(UTC).isoformat(),
        "actor": current_actor(),
        "host": host,
        "command_name": command_name,
        "command": command,
        "exit_status": exit_status,
        "error": error,
    }
    logger.info("audit %s", entry)

    path = Path(os.environ.get("RCA_AUDIT_LOG_PATH", DEFAULT_AUDIT_LOG_PATH))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def reject(target: str, command_name: str, error: Exception) -> None:
    record_event(host=target, command_name=command_name, command=None, exit_status=None, error=str(error))
    raise error
