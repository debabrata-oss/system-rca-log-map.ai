from dataclasses import dataclass
from typing import Callable

from rca_log_map.controller.validation import (
    validate_boot_offset,
    validate_day,
    validate_enum,
    validate_lines,
    validate_since,
    validate_unit_name,
)

WEB_LOG_PATHS = {
    "httpd": "/var/log/httpd/error_log",
    "nginx": "/var/log/nginx/error.log",
}


@dataclass(frozen=True)
class CommandSpec:
    description: str
    render: Callable[..., str]


def _journalctl_recent_errors(lines: int = 200) -> str:
    lines = validate_lines(lines)
    return f"journalctl -xe -n {lines} --no-pager"


def _journalctl_boot(boot_offset: int = 0, lines: int = 200) -> str:
    boot_offset = validate_boot_offset(boot_offset)
    lines = validate_lines(lines)
    return f"journalctl -b {boot_offset} --no-pager -n {lines}"


def _journalctl_service(unit: str, since: str = "1 hour ago", lines: int = 200) -> str:
    unit = validate_unit_name(unit)
    since = validate_since(since)
    lines = validate_lines(lines)
    return f'journalctl -u {unit} --since "{since}" --no-pager -n {lines}'


def _system_messages(lines: int = 200) -> str:
    lines = validate_lines(lines)
    return f"tail -n {lines} /var/log/messages"


def _auth_log(lines: int = 200) -> str:
    lines = validate_lines(lines)
    return f"tail -n {lines} /var/log/secure"


def _kernel_log(lines: int = 200) -> str:
    lines = validate_lines(lines)
    return f"dmesg -T | tail -n {lines}"


def _selinux_denials(window: str = "recent") -> str:
    window = validate_enum(window, ("recent", "today", "this-week"))
    return f"ausearch -m avc -ts {window}"


def _cron_log(lines: int = 200) -> str:
    lines = validate_lines(lines)
    return f"tail -n {lines} /var/log/cron"


def _package_log(lines: int = 200) -> str:
    lines = validate_lines(lines)
    return f"tail -n {lines} /var/log/dnf.log"


def _web_log(server: str = "httpd", lines: int = 200) -> str:
    server = validate_enum(server, tuple(WEB_LOG_PATHS))
    lines = validate_lines(lines)
    return f"tail -n {lines} {WEB_LOG_PATHS[server]}"


def _sar_stats(day: int | None = None) -> str:
    day = validate_day(day)
    if day is None:
        return "sar"
    return f"sar -f /var/log/sa/sa{day:02d}"


COMMAND_REGISTRY: dict[str, CommandSpec] = {
    "journalctl_recent_errors": CommandSpec(
        description="Most recent systemd journal entries with error context (journalctl -xe).",
        render=_journalctl_recent_errors,
    ),
    "journalctl_boot": CommandSpec(
        description="Journal for the current (0) or previous (-1) boot.",
        render=_journalctl_boot,
    ),
    "journalctl_service": CommandSpec(
        description="Per-service failure timeline (journalctl -u <unit> --since <window>).",
        render=_journalctl_service,
    ),
    "system_messages": CommandSpec(
        description="General system/daemon messages from /var/log/messages.",
        render=_system_messages,
    ),
    "auth_log": CommandSpec(
        description="SSH, sudo, and auth failures/logins from /var/log/secure.",
        render=_auth_log,
    ),
    "kernel_log": CommandSpec(
        description="Kernel messages (OOM-kills, disk/HW errors, driver issues) via dmesg -T.",
        render=_kernel_log,
    ),
    "selinux_denials": CommandSpec(
        description="SELinux AVC denials via ausearch -m avc.",
        render=_selinux_denials,
    ),
    "cron_log": CommandSpec(
        description="Cron/timer job runs from /var/log/cron.",
        render=_cron_log,
    ),
    "package_log": CommandSpec(
        description="Package install/update history from /var/log/dnf.log.",
        render=_package_log,
    ),
    "web_log": CommandSpec(
        description="App/web layer error log for httpd or nginx.",
        render=_web_log,
    ),
    "sar_stats": CommandSpec(
        description="Historical CPU/mem/IO/net stats via sar, optionally for a given day of month.",
        render=_sar_stats,
    ),
}
