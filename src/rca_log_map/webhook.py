import json
import logging
import os
import re
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

from rca_log_map.rca.agent import investigate

logger = logging.getLogger(__name__)

DEFAULT_REPORTS_DIR = "reports"
UNSAFE_FILENAME_CHARS_RE = re.compile(r"[^A-Za-z0-9_.-]")


def _safe_filename_component(value: str) -> str:
    # alert.host is attacker-controlled (from the webhook payload) and must
    # never be allowed to inject path separators or ".." into a filesystem
    # path -- this is purely for building a safe filename, not a host allowlist
    # check (that already happens inside investigate() via get_host()).
    return UNSAFE_FILENAME_CHARS_RE.sub("_", value)[:100]


class AlertPayload(BaseModel):
    host: str
    reason: str
    since: str | None = None
    max_iterations: int = 6


def _parse_alertmanager_payload(body: dict) -> list[AlertPayload]:
    by_host: dict[str, list[str]] = {}
    for alert in body.get("alerts", []):
        if alert.get("status") != "firing":
            continue
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        host = labels.get("instance") or labels.get("host")
        if not host:
            continue
        reason = (
            annotations.get("summary")
            or annotations.get("description")
            or labels.get("alertname")
            or "alert fired"
        )
        by_host.setdefault(host, []).append(reason)

    return [
        AlertPayload(host=host, reason="; ".join(reasons))
        for host, reasons in by_host.items()
    ]


def parse_webhook_payload(body: dict) -> list[AlertPayload]:
    if "alerts" in body:
        return _parse_alertmanager_payload(body)
    return [AlertPayload(**body)]


def _reports_dir() -> Path:
    return Path(os.environ.get("RCA_REPORTS_DIR", DEFAULT_REPORTS_DIR))


def _save_report(alert: AlertPayload, outcome: dict) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
    safe_host = _safe_filename_component(alert.host)
    path = _reports_dir() / f"{timestamp}_{safe_host}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "triggered_at": datetime.now(UTC).isoformat(),
        "alert": alert.model_dump(),
        **outcome,
    }
    path.write_text(json.dumps(record, indent=2))
    return path


def run_triggered_investigation(alert: AlertPayload) -> None:
    try:
        result = investigate(alert.host, alert.reason, max_iterations=alert.max_iterations)
    except Exception as exc:
        # Broad on purpose: nothing is watching this background task's result in
        # real time, so any failure (bad host, SSH error, Claude API error, ...)
        # must still leave a record instead of vanishing into BackgroundTasks.
        logger.exception("triggered investigation failed for host=%s", alert.host)
        _save_report(alert, {"status": "error", "error": str(exc)})
        return

    path = _save_report(alert, {"status": "ok", "result": result.model_dump()})
    logger.info("triggered investigation for host=%s written to %s", alert.host, path)
