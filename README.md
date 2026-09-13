# system-rca-log-map.ai

Live server introspection and post-incident root-cause-analysis log collection, exposed as MCP tools with a CLI and web UI on top.

See [`PLAN.md`](PLAN.md) for the original idea and log-source reference, and [`docs/ROADMAP.md`](docs/ROADMAP.md) for the phased build plan.

## Status

Phases 0-3 done: log-collection tools (MCP + CLI), a Claude-based RCA
investigation loop, and a minimal web UI. See `docs/ROADMAP.md` for what's next.

## Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
pip install pytest httpx  # dev-only deps
pytest
```

## Usage

1. `cp config/hosts.example.yaml config/hosts.yaml` and fill in your host(s).
2. `export ANTHROPIC_API_KEY=...`
3. CLI: `rca list-sources`, `rca collect --host <alias> --source <name>`, `rca investigate --host <alias> --question "..."`
4. MCP server (stdio): `rca-mcp`
5. Web UI: `RCA_WEB_API_KEY=<pick-a-key> rca-web`, then open `http://localhost:8000`
