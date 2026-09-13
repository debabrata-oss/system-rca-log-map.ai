import paramiko
import typer

from rca_log_map.config import load_hosts
from rca_log_map.controller.commands import COMMAND_REGISTRY
from rca_log_map.tools import log_tools

app = typer.Typer(help="rca: collect and analyze Linux host/cluster logs for RCA.")

_SOURCE_FUNCS = {fn.__name__: fn for fn in log_tools.ALL_TOOLS}


@app.command("list-sources")
def list_sources() -> None:
    """List available log sources and what each one collects."""
    for name, spec in COMMAND_REGISTRY.items():
        typer.echo(f"{name}: {spec.description}")


@app.command("list-hosts")
def list_hosts() -> None:
    """List configured host aliases (never prints keys or secrets)."""
    try:
        hosts = load_hosts()
    except FileNotFoundError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    if not hosts:
        typer.echo("No hosts configured. See config/hosts.example.yaml.")
        return
    for alias, host in hosts.items():
        typer.echo(f"{alias}: {host.username}@{host.hostname}:{host.port}")


@app.command()
def collect(
    host: str = typer.Option(..., help="Host alias from config/hosts.yaml."),
    source: str = typer.Option(..., help="Log source name; see `rca list-sources`."),
    lines: int = typer.Option(None, help="Number of lines to return, where applicable."),
    unit: str = typer.Option(None, help="systemd unit name (journalctl_service only)."),
    since: str = typer.Option(None, help="Time window, e.g. '2 hours ago' (journalctl_service only)."),
    boot_offset: int = typer.Option(None, help="0=current boot, -1=previous (journalctl_boot only)."),
    window: str = typer.Option(None, help="recent/today/this-week (selinux_denials only)."),
    server: str = typer.Option(None, help="httpd/nginx (web_log only)."),
    day: int = typer.Option(None, help="Day of month 1-31 (sar_stats only)."),
) -> None:
    """Collect one log source from a configured host."""
    if source not in _SOURCE_FUNCS:
        typer.echo(f"Unknown source {source!r}. Run `rca list-sources` to see options.", err=True)
        raise typer.Exit(code=1)

    kwargs = {"host": host}
    for name, value in (
        ("lines", lines),
        ("unit", unit),
        ("since", since),
        ("boot_offset", boot_offset),
        ("window", window),
        ("server", server),
        ("day", day),
    ):
        if value is not None:
            kwargs[name] = value

    try:
        result = _SOURCE_FUNCS[source](**kwargs)
    except (KeyError, ValueError, FileNotFoundError, OSError, paramiko.SSHException) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(result)


if __name__ == "__main__":
    app()
