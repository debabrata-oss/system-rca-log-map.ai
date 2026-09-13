import getpass
import subprocess

import anthropic
import paramiko
import typer

from rca_log_map import audit
from rca_log_map.config import load_clusters, load_hosts
from rca_log_map.controller.commands import COMMAND_REGISTRY
from rca_log_map.controller.kubectl_commands import KUBECTL_COMMAND_REGISTRY
from rca_log_map.rca.agent import investigate as run_investigation
from rca_log_map.tools import k8s_tools, log_tools

app = typer.Typer(help="rca: collect and analyze Linux host/cluster logs for RCA.")

_SOURCE_FUNCS = {fn.__name__: fn for fn in log_tools.ALL_TOOLS}
_K8S_SOURCE_FUNCS = {fn.__name__: fn for fn in k8s_tools.ALL_K8S_TOOLS}


@app.callback()
def main_callback() -> None:
    audit.set_actor(getpass.getuser())


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


@app.command("list-clusters")
def list_clusters() -> None:
    """List configured cluster aliases (never prints kubeconfig contents)."""
    try:
        clusters = load_clusters()
    except FileNotFoundError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    if not clusters:
        typer.echo("No clusters configured. See config/clusters.example.yaml.")
        return
    for alias, cluster in clusters.items():
        typer.echo(f"{alias}: context={cluster.context or '(default)'} kubeconfig={cluster.kubeconfig_path}")


@app.command("list-k8s-sources")
def list_k8s_sources() -> None:
    """List available Kubernetes log sources and what each one collects."""
    for name, spec in KUBECTL_COMMAND_REGISTRY.items():
        typer.echo(f"{name}: {spec.description}")


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
    except (KeyError, ValueError, FileNotFoundError, PermissionError, OSError, paramiko.SSHException) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(result)


@app.command("k8s-collect")
def k8s_collect(
    cluster: str = typer.Option(..., help="Cluster alias from config/clusters.yaml."),
    source: str = typer.Option(..., help="Log source name; see `rca list-k8s-sources`."),
    pod: str = typer.Option(None, help="Pod name (k8s_describe_pod, k8s_pod_logs)."),
    namespace: str = typer.Option(None, help="Namespace, default 'default' (describe_pod/pod_logs)."),
    container: str = typer.Option(None, help="Container name (k8s_pod_logs only)."),
    previous: bool = typer.Option(False, help="Previous crashed instance's logs (k8s_pod_logs only)."),
    lines: int = typer.Option(None, help="Number of lines to return (k8s_pod_logs only)."),
) -> None:
    """Collect one Kubernetes log source from a configured cluster."""
    if source not in _K8S_SOURCE_FUNCS:
        typer.echo(f"Unknown source {source!r}. Run `rca list-k8s-sources` to see options.", err=True)
        raise typer.Exit(code=1)

    kwargs = {"cluster": cluster}
    for name, value in (
        ("pod", pod),
        ("namespace", namespace),
        ("container", container),
        ("lines", lines),
    ):
        if value is not None:
            kwargs[name] = value
    if previous:
        kwargs["previous"] = True

    try:
        result = _K8S_SOURCE_FUNCS[source](**kwargs)
    except (
        KeyError, ValueError, FileNotFoundError, PermissionError,
        OSError, subprocess.SubprocessError,
    ) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(result)


@app.command()
def investigate(
    host: str = typer.Option(..., help="Host alias from config/hosts.yaml."),
    question: str = typer.Option(..., help="Plain-language description of the incident to investigate."),
    max_iterations: int = typer.Option(6, help="Max Claude tool-use turns before forcing a final report."),
) -> None:
    """Ask Claude to investigate an incident on a host and produce an RCA report."""
    try:
        result = run_investigation(host, question, max_iterations=max_iterations)
    except (
        KeyError, ValueError, FileNotFoundError, PermissionError,
        OSError, paramiko.SSHException, RuntimeError, anthropic.APIError,
    ) as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    report = result.report
    typer.echo(f"Host: {report.host}")
    typer.echo(f"Summary: {report.summary}")
    typer.echo(f"Likely root cause: {report.likely_root_cause}")
    typer.echo(f"Confidence: {report.confidence}")
    typer.echo("Evidence:")
    for item in report.evidence:
        typer.echo(f"  - {item}")
    typer.echo("Recommended actions:")
    for item in report.recommended_actions:
        typer.echo(f"  - {item}")
    typer.echo(f"Tools used: {', '.join(report.tools_used) or '(none)'}")


if __name__ == "__main__":
    app()
