from rca_log_map import audit
from rca_log_map.config import get_host
from rca_log_map.controller.commands import COMMAND_REGISTRY
from rca_log_map.controller.ssh_controller import SSHController


def _run(host: str, command_name: str, **params) -> str:
    if command_name not in COMMAND_REGISTRY:
        error = KeyError(f"Unknown command {command_name!r}; not in COMMAND_REGISTRY")
        audit.reject(host, command_name, error)

    try:
        host_config = get_host(host)
    except (KeyError, FileNotFoundError) as exc:
        audit.reject(host, command_name, exc)

    if not host_config.is_source_allowed(command_name):
        audit.reject(
            host,
            command_name,
            PermissionError(f"{command_name!r} is not permitted on host {host!r}"),
        )

    # Validate/render before opening any connection so bad params fail fast,
    # client-side, instead of wasting a connection attempt. SSHController.run()
    # re-validates as defense in depth.
    try:
        COMMAND_REGISTRY[command_name].render(**params)
    except ValueError as exc:
        audit.reject(host, command_name, exc)

    with SSHController(host, host_config) as ctl:
        result = ctl.run(command_name, **params)
    if result.exit_status != 0:
        return (
            f"[{command_name} on {host} exited {result.exit_status}]\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result.stdout


def journalctl_recent_errors(host: str, lines: int = 200) -> str:
    """Most recent systemd journal entries with error context (journalctl -xe) on a host."""
    return _run(host, "journalctl_recent_errors", lines=lines)


def journalctl_boot(host: str, boot_offset: int = 0, lines: int = 200) -> str:
    """Journal for the current (boot_offset=0) or previous (boot_offset=-1) boot on a host."""
    return _run(host, "journalctl_boot", boot_offset=boot_offset, lines=lines)


def journalctl_service(host: str, unit: str, since: str = "1 hour ago", lines: int = 200) -> str:
    """Per-service failure timeline for a systemd unit since a given time window."""
    return _run(host, "journalctl_service", unit=unit, since=since, lines=lines)


def system_messages(host: str, lines: int = 200) -> str:
    """General system/daemon messages from /var/log/messages on a host."""
    return _run(host, "system_messages", lines=lines)


def auth_log(host: str, lines: int = 200) -> str:
    """SSH, sudo, and auth failures/logins from /var/log/secure on a host."""
    return _run(host, "auth_log", lines=lines)


def kernel_log(host: str, lines: int = 200) -> str:
    """Kernel messages (OOM-kills, disk/HW errors, driver issues) via dmesg -T on a host."""
    return _run(host, "kernel_log", lines=lines)


def selinux_denials(host: str, window: str = "recent") -> str:
    """SELinux AVC denials via ausearch -m avc for a time window (recent/today/this-week)."""
    return _run(host, "selinux_denials", window=window)


def cron_log(host: str, lines: int = 200) -> str:
    """Cron/timer job runs from /var/log/cron on a host."""
    return _run(host, "cron_log", lines=lines)


def package_log(host: str, lines: int = 200) -> str:
    """Package install/update history from /var/log/dnf.log on a host."""
    return _run(host, "package_log", lines=lines)


def web_log(host: str, server: str = "httpd", lines: int = 200) -> str:
    """App/web layer error log for httpd or nginx on a host."""
    return _run(host, "web_log", server=server, lines=lines)


def sar_stats(host: str, day: int | None = None) -> str:
    """Historical CPU/mem/IO/net stats via sar, optionally for a given day of month (1-31)."""
    return _run(host, "sar_stats", day=day)


def crictl_ps(host: str) -> str:
    """List running and exited containers on a node via crictl ps -a."""
    return _run(host, "crictl_ps")


def crictl_logs(host: str, container_id: str, lines: int = 200, previous: bool = False) -> str:
    """Container runtime logs for a specific container ID via crictl logs."""
    return _run(host, "crictl_logs", container_id=container_id, lines=lines, previous=previous)


def pcs_status(host: str) -> str:
    """Pacemaker/Corosync resource, node, and quorum state via pcs status."""
    return _run(host, "pcs_status")


def crm_mon_status(host: str) -> str:
    """Pacemaker/Corosync resource, node, and quorum state via crm_mon -1."""
    return _run(host, "crm_mon_status")


def pacemaker_log(host: str, lines: int = 200) -> str:
    """Resource start/stop/failover and fencing events from /var/log/pacemaker/pacemaker.log."""
    return _run(host, "pacemaker_log", lines=lines)


def corosync_log(host: str, lines: int = 200) -> str:
    """Membership, quorum, and split-brain events from /var/log/cluster/corosync.log."""
    return _run(host, "corosync_log", lines=lines)


def journalctl_ha_cluster(host: str, since: str = "1 hour ago", lines: int = 200) -> str:
    """Combined pacemaker + corosync timeline via journalctl -u pacemaker -u corosync."""
    return _run(host, "journalctl_ha_cluster", since=since, lines=lines)


ALL_TOOLS = (
    journalctl_recent_errors,
    journalctl_boot,
    journalctl_service,
    system_messages,
    auth_log,
    kernel_log,
    selinux_denials,
    cron_log,
    package_log,
    web_log,
    sar_stats,
    crictl_ps,
    crictl_logs,
    pcs_status,
    crm_mon_status,
    pacemaker_log,
    corosync_log,
    journalctl_ha_cluster,
)
