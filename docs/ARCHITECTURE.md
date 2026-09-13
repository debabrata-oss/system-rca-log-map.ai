# Architecture: end-to-end flow

## Request flow

How a question (from the CLI, the web UI, or an alerting webhook) turns into a real RCA report.

```mermaid
flowchart TD
    CLI["CLI (rca collect / investigate / k8s-collect)"]
    WebUI["Web UI"]
    Webhook["Alerting Webhook (Alertmanager or generic JSON)"]
    API["FastAPI app (/api/hosts, /api/investigate)"]
    WHRoute["/webhook/alert (API key: header or query param)"]
    Parse["parse_webhook_payload (dedupe by host, firing only)"]
    BG["BackgroundTasks (202 returned immediately)"]
    Agent["RCA Agent (Claude tool-use loop, bounded iterations)"]
    Claude[("Anthropic API")]
    Dispatch{"Tool dispatch"}
    G1["Host allowlist + per-host policy + param validation"]
    G2["Cluster allowlist + per-cluster policy + param validation"]
    SSH["SSHController (paramiko, RejectPolicy, known_hosts required)"]
    KC["KubectlController (subprocess argv, no shell string)"]
    Targets[("RHEL/systemd hosts, K8s nodes, HA cluster nodes")]
    K8sAPI[("Kubernetes API server")]
    Audit[("logs/audit.log — every attempt: allowed, denied, or errored")]
    Result["RCAReport + transcript"]
    Reports[("reports/*.json")]

    WebUI --> API
    Webhook --> WHRoute --> Parse --> BG
    API --> Agent
    BG --> Agent
    CLI --> Dispatch

    Agent <--> Claude
    Agent --> Dispatch

    Dispatch -->|host-scoped tool| G1 --> SSH
    Dispatch -->|cluster-scoped tool| G2 --> KC

    SSH -->|SSH exec| Targets
    KC -->|kubectl| K8sAPI

    SSH --> Audit
    KC --> Audit

    Agent --> Result --> API
    Result -.->|webhook path only| Reports
```

Key properties this diagram is meant to make visible:
- **Every path converges on the same guardrail choke point** (`G1`/`G2`) before any command reaches a real host or cluster — the CLI, the web API, and the Claude agent's own tool calls all go through identical allowlist/policy/validation checks, not three separate implementations.
- **The webhook path never blocks the caller** — it returns `202` immediately and runs the investigation in the background, persisting the outcome (success or error) to `reports/` since nothing is watching the HTTP response.
- **`SSHController` and `KubectlController` are the only two places that ever touch a real target** — SSH commands are built from validated templates (never a raw shell string), kubectl calls are built as an argv list (never a shell string at all).
- **Audit logging is unified** regardless of target kind — a host and a cluster both write to the same `logs/audit.log`.

## Deployment pipeline

How a code change becomes a running pod.

```mermaid
flowchart LR
    Dev["git push to main"] --> CI["GitHub Actions CI (pytest, ruff)"]
    CI --> Build["Docker build (multi-stage, non-root)"]
    Build --> GHCR[("ghcr.io image, tagged :latest and :sha")]
    GHCR --> Deploy["kubectl apply -k deploy/k8s/base"]
    Deploy --> Pod["rca-web pod"]
    Pod -->|liveness/readiness probes| Healthz["GET /healthz"]
```

CI gates the image push to `main` only (PRs build-check without publishing). The Kubernetes `Deployment` pulls by tag, and `automountServiceAccountToken: false` plus a non-root `securityContext` keep the pod itself minimally privileged — it authenticates to target hosts/clusters via explicitly mounted credentials (an SSH key, a kubeconfig), never its own pod identity.
