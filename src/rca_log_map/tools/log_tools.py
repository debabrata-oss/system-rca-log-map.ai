from rca_log_map import audit
from rca_log_map.config import get_host
from rca_log_map.controller.commands import COMMAND_REGISTRY
from rca_log_map.controller.ssh_controller import SSHController


def _reject(host: str, command_name: str, error: Exception) -> None:
    audit.record_event(
        host=host, command_name=command_name, command=None, exit_status=None, error=str(error)
    )
    raise error


def _run(host: str, command_name: str, **params) -> str:
    if command_name not in COMMAND_REGISTRY:
        _reject(host, command_name, KeyError(f"Unknown command {command_name!r}; not in COMMAND_REGISTRY"))

    try:
        host_config = get_host(host)
    except (KeyError, FileNotFoundError) as exc:
        _reject(host, command_name, exc)

    if not host_config.is_source_allowed(command_name):
        _reject(
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
        _reject(host, command_name, exc)

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
)
