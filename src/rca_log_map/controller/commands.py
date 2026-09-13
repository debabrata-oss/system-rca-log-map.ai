from dataclasses import dataclass
from typing import Callable

from rca_log_map.controller.validation import (
    validate_boot_offset,
    validate_container_id,
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


def _crictl_ps() -> str:
    return "crictl ps -a"


def _crictl_logs(container_id: str, lines: int = 200, previous: bool = False) -> str:
    container_id = validate_container_id(container_id)
    lines = validate_lines(lines)
    flag = " -p" if previous else ""
    return f"crictl logs --tail {lines}{flag} {container_id}"


def _pcs_status() -> str:
    return "pcs status"


def _crm_mon_status() -> str:
    return "crm_mon -1"


def _pacemaker_log(lines: int = 200) -> str:
    lines = validate_lines(lines)
    return f"tail -n {lines} /var/log/pacemaker/pacemaker.log"


def _corosync_log(lines: int = 200) -> str:
    lines = validate_lines(lines)
    return f"tail -n {lines} /var/log/cluster/corosync.log"


def _journalctl_ha_cluster(since: str = "1 hour ago", lines: int = 200) -> str:
    since = validate_since(since)
    lines = validate_lines(lines)
    return f'journalctl -u pacemaker -u corosync --since "{since}" --no-pager -n {lines}'


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
    "crictl_ps": CommandSpec(
        description="List running and exited containers on a node (crictl ps -a).",
        render=_crictl_ps,
    ),
    "crictl_logs": CommandSpec(
        description="Container runtime logs for a specific container ID (crictl logs).",
        render=_crictl_logs,
    ),
    "pcs_status": CommandSpec(
        description="Pacemaker/Corosync resource, node, and quorum state (pcs status).",
        render=_pcs_status,
    ),
    "crm_mon_status": CommandSpec(
        description="Pacemaker/Corosync resource, node, and quorum state (crm_mon -1).",
        render=_crm_mon_status,
    ),
    "pacemaker_log": CommandSpec(
        description="Resource start/stop/failover and fencing events from /var/log/pacemaker/pacemaker.log.",
        render=_pacemaker_log,
    ),
    "corosync_log": CommandSpec(
        description="Membership, quorum, and split-brain events from /var/log/cluster/corosync.log.",
        render=_corosync_log,
    ),
    "journalctl_ha_cluster": CommandSpec(
        description="Combined pacemaker + corosync timeline (journalctl -u pacemaker -u corosync).",
        render=_journalctl_ha_cluster,
    ),
}
