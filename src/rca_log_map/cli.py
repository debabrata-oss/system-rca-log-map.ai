import typer

app = typer.Typer(help="rca: collect and analyze Linux host/cluster logs for RCA.")


@app.command()
def collect(
    host: str = typer.Option(..., help="Target host to collect logs from."),
    since: str = typer.Option("1 hour ago", help="Start of the time window, e.g. '2 hours ago'."),
) -> None:
    """Collect the standalone RHEL/systemd log set from a target host."""
    raise NotImplementedError("Phase 1: wire this up to rca_log_map.controller")


if __name__ == "__main__":
    app()
