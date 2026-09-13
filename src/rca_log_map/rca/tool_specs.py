from typing import Any, Callable

from rca_log_map.controller.commands import COMMAND_REGISTRY
from rca_log_map.tools import log_tools

LINES_PROPERTY = {
    "type": "integer",
    "description": "Number of lines to return (default 200, hard max 2000).",
}

# JSON Schema "properties" for each tool's parameters, excluding `host` --
# the investigation is scoped to one host for its whole run, bound once by
# the agent rather than left for Claude to (mis)supply on every call.
_PARAM_SCHEMAS: dict[str, dict[str, Any]] = {
    "journalctl_recent_errors": {"lines": LINES_PROPERTY},
    "journalctl_boot": {
        "boot_offset": {
            "type": "integer",
            "enum": [0, -1],
            "description": "0 for the current boot, -1 for the previous boot.",
        },
        "lines": LINES_PROPERTY,
    },
    "journalctl_service": {
        "unit": {"type": "string", "description": "systemd unit name, e.g. 'sshd'."},
        "since": {
            "type": "string",
            "description": "Time window, e.g. '2 hours ago', 'today', or 'YYYY-MM-DD [HH:MM[:SS]]'.",
        },
        "lines": LINES_PROPERTY,
    },
    "system_messages": {"lines": LINES_PROPERTY},
    "auth_log": {"lines": LINES_PROPERTY},
    "kernel_log": {"lines": LINES_PROPERTY},
    "selinux_denials": {
        "window": {
            "type": "string",
            "enum": ["recent", "today", "this-week"],
            "description": "Time window for SELinux AVC denials.",
        }
    },
    "cron_log": {"lines": LINES_PROPERTY},
    "package_log": {"lines": LINES_PROPERTY},
    "web_log": {
        "server": {"type": "string", "enum": ["httpd", "nginx"]},
        "lines": LINES_PROPERTY,
    },
    "sar_stats": {
        "day": {
            "type": "integer",
            "description": "Day of month (1-31) for a historical sar file; omit for today's stats.",
        }
    },
    "crictl_ps": {},
    "crictl_logs": {
        "container_id": {"type": "string", "description": "Container ID from crictl_ps output."},
        "lines": LINES_PROPERTY,
        "previous": {"type": "boolean", "description": "Logs from a previous crashed instance."},
    },
}

_REQUIRED_PARAMS: dict[str, list[str]] = {
    "journalctl_service": ["unit"],
    "crictl_logs": ["container_id"],
}

LOG_TOOL_DISPATCH: dict[str, Callable[..., str]] = {fn.__name__: fn for fn in log_tools.ALL_TOOLS}

LOG_TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": name,
        "description": COMMAND_REGISTRY[name].description,
        "input_schema": {
            "type": "object",
            "properties": _PARAM_SCHEMAS[name],
            "required": _REQUIRED_PARAMS.get(name, []),
        },
    }
    for name in LOG_TOOL_DISPATCH
]

SUBMIT_REPORT_TOOL: dict[str, Any] = {
    "name": "submit_rca_report",
    "description": (
        "Submit the final root-cause-analysis report once you have gathered enough evidence. "
        "Call this exactly once, as your final action."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {"type": "string", "description": "One or two sentence summary of what happened."},
            "likely_root_cause": {"type": "string"},
            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
            "evidence": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific log lines or facts that support the root cause.",
            },
            "recommended_actions": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": ["summary", "likely_root_cause", "confidence", "evidence", "recommended_actions"],
    },
}
