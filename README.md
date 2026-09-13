# system-rca-log-map.ai

Live server introspection and post-incident root-cause-analysis log collection, exposed as MCP tools with a CLI and web UI on top.

See [`PLAN.md`](PLAN.md) for the original idea and log-source reference, [`docs/ROADMAP.md`](docs/ROADMAP.md) for the phased build plan, and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for an end-to-end flow diagram (request flow + deployment pipeline).

## Status

All 8 roadmap phases done: log-collection tools for standalone RHEL/systemd,
Kubernetes, and Pacemaker/Corosync HA clusters (MCP + CLI), a Claude-based RCA
investigation loop, a minimal web UI, guardrails/audit logging, an alerting
webhook for automatic triggers, and Docker/Kubernetes deployment. See
`docs/ROADMAP.md` for the full phase history.

## Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
ruff check .
pytest
```

## Usage

1. `cp config/hosts.example.yaml config/hosts.yaml` and fill in your host(s).
2. `export ANTHROPIC_API_KEY=...`
3. CLI: `rca list-sources`, `rca collect --host <alias> --source <name>`, `rca investigate --host <alias> --question "..."`
4. MCP server (stdio): `rca-mcp`
5. Web UI: `RCA_WEB_API_KEY=<pick-a-key> rca-web`, then open `http://localhost:8000`
6. Kubernetes: `cp config/clusters.example.yaml config/clusters.yaml`, fill in a kubeconfig, then `rca list-k8s-sources`, `rca k8s-collect --cluster <alias> --source <name>`
7. Alerting webhook: `POST /webhook/alert` with `X-API-Key` header or `?api_key=` query param, either `{"host": "web1", "reason": "..."}` or Prometheus Alertmanager's native `webhook_configs` payload shape. Triggers a standalone-host investigation automatically; the report (or error, if it failed) is written to `reports/<timestamp>_<host>.json`.

## Deployment

**Local (Docker Compose) -- verify the image before touching a cluster:**

```bash
cp .env.example .env   # fill in RCA_WEB_API_KEY / ANTHROPIC_API_KEY
cp config/hosts.example.yaml config/hosts.yaml   # fill in real hosts
docker compose up --build
curl localhost:8000/healthz
```
Mounts `./config` into the container and your `~/.ssh` (for `known_hosts` and any private keys `hosts.yaml` references) -- note the container runs as a non-root user (UID 1000), so if your local key files aren't readable by that UID the container won't be able to use them; this is a local-verification convenience, not how the Kubernetes deployment mounts credentials (see below).

**Kubernetes:**

`SSHController` uses `paramiko.RejectPolicy()`, so **every target host needs an entry in a mounted `known_hosts` file or its SSH connections fail closed** -- this is easy to miss.

1. Build/push happens automatically via CI (`.github/workflows/ci.yml`) on merge to `main`, publishing `ghcr.io/<owner>/<repo>:latest`. To use a different registry, edit the `image:` field in `deploy/k8s/base/deployment.yaml`.
2. Copy and fill in the two credential templates, then apply them directly (they're intentionally *not* part of the kustomization, same convention as `config/hosts.example.yaml`):
   ```bash
   cp deploy/k8s/base/secret.example.yaml /tmp/secret.yaml            # edit, then:
   kubectl apply -f /tmp/secret.yaml
   cp deploy/k8s/base/known-hosts-configmap.example.yaml /tmp/kh.yaml # edit (ssh-keyscan output), then:
   kubectl apply -f /tmp/kh.yaml
   ```
3. `kubectl apply -k deploy/k8s/base`
4. Optionally adapt and apply `deploy/k8s/base/ingress.example.yaml` for external access (it needs an `ingressClassName` matching your cluster).

Logs/reports are on an `emptyDir` volume (survives container restarts, not pod rescheduling) -- mount a PVC instead if you need them to persist across rescheduling.
