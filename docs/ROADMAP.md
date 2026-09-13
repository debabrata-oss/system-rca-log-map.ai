# Roadmap: system-rca-log-map.ai

## Context

The user has a rough brain-dump in `PLAN.md` for a Linux log-analysis / RCA tool: query a live server for what's happening now, and after an incident, automatically pull the relevant logs and use an LLM to explain what broke and what to do next. `PLAN.md` also lists the log sources across three environments (standalone RHEL/systemd, Kubernetes, Pacemaker/Corosync HA clusters) but has no code or repo yet — this is a 0-to-1 project. The goal of this task is to turn that brain-dump into a structured, phased roadmap document the user can execute against, plus a recommendation of existing Claude Code skills (from skills.sh) that will speed up building it. No code is being written in this task — the deliverable is the roadmap itself.

## Architecture decisions (confirmed with user)

- **Language:** Python for the MCP server, tool implementations, and RCA logic.
- **Collection architecture:** Centralized controller that SSHes into target hosts/nodes and runs an allowlisted set of read-only commands (journalctl, kubectl, pcs status, etc). No per-host agent for v1; noted as a possible later phase for scale.
- **Phase 1 environment scope:** Standalone RHEL/systemd only. Kubernetes and Pacemaker/Corosync HA cluster support come in later phases, reusing the same tool/controller pattern.
- **Trigger model:** Manual trigger via chat/CLI ("investigate what happened between X and Y") for v1. Alerting-integration and local-watcher auto-triggers are later-phase options.
- **LLM:** Claude via the Anthropic API directly for v1, called through a thin interface so other providers could be swapped in later without a rewrite.
- **Web UI:** A minimal custom chat UI (e.g. FastAPI backend + simple frontend) that shows tool calls, log excerpts, and the final RCA report inline — not a generic reused MCP chat client.
- **Access control:** Greenfield, no existing SSO/LDAP to integrate. v1 guardrails = allowlisted read-only commands per host, a dedicated restricted service account (sudoers allowlist, no write access), and basic API-key/auth on the web UI.
- **Repo/deploy:** New GitHub repo for this project. Docker/Kubernetes package *the tool itself* (web UI + MCP server + controller) — not the servers being monitored, which are reached over SSH from the controller.

## Recommended Claude Code skills to install (from skills.sh)

These are third-party skills discovered via skills.sh that match the stack above. Each is installed with `npx skills add <repo-url> --skill <name>` (run this — it's a filesystem-modifying command, so do it as an explicit step, not silently). All listed ones passed Agent Trust Hub / Socket / Snyk audits per their skills.sh pages.

| Skill | Why it fits this project | Install |
|---|---|---|
| `fastapi-pro` (sickn33/agentic-awesome-skills) | The web UI backend is FastAPI-shaped; gives async API patterns, project checklists. | `npx skills add https://github.com/sickn33/agentic-awesome-skills --skill fastapi-pro` |
| `docker-expert` (sickn33/agentic-awesome-skills) | Multi-stage builds, hardening, and production Dockerfile patterns for containerizing the controller/web UI. | `npx skills add https://github.com/sickn33/agentic-awesome-skills --skill docker-expert` |
| `kubernetes` (mindrally/skills) | Least-privilege, IaC-style conventions for the K8s manifests that will deploy this tool (and later, for the Phase-4 k8s log-collection tools themselves). | `npx skills add https://github.com/mindrally/skills --skill kubernetes` |
| `devops-engineer` (jeffallan/claude-skills) | Broad CI/CD + deploy + incident-response framing, useful once the GitHub repo/CI and rollout phases start. | `npx skills add https://github.com/jeffallan/claude-skills --skill devops-engineer` |
| `systematic-debugging` (obra/superpowers) | Enforces root-cause-first investigation (evidence → hypothesis → fix) — directly matches the RCA methodology this tool should encode, and is useful for debugging the tool's own code too. | `npx skills add https://github.com/obra/superpowers --skill systematic-debugging` |

Already available in this Claude Code session (no install needed) and worth leaning on as the project develops: `security-review` (guardrails/access-control review before shipping the SSH controller), `code-review` (reviewing PRs against the new repo), and `init` (to scaffold a good `CLAUDE.md` once code exists).

Skills.sh had no direct hit for "systemd/journalctl RCA" specifically — that domain knowledge is what this project *is*, so it's encoded in the roadmap's own tool design below rather than borrowed from a skill.

## Phased roadmap

**Phase 0 — Repo & tooling setup**
- Create the GitHub repo; scaffold Python project (uv/poetry, src layout, tests dir).
- Install the skills.sh skills above.
- Write `CLAUDE.md` (via `init` once there's code) capturing conventions as they emerge.

**Phase 1 — Core MCP tools + CLI (standalone RHEL/systemd)**
- Implement an SSH-based controller module: connects to a target host with a restricted service account, runs an allowlisted command set from `PLAN.md`'s standalone table (`journalctl -xe`, `journalctl -u <svc>`, `/var/log/messages`, `/var/log/secure`, `dmesg -T`, `ausearch`/`aureport`, `/var/log/cron`, `/var/log/dnf.log`, web server logs, `sar`).
- Wrap each command as an MCP tool (one tool per log source, or a small number of parameterized tools) with strict input validation (host allowlist, time-window bounds, no arbitrary shell).
- Ship a Unix-like CLI (e.g. `rca collect --host X --since "1 hour ago"`) as the first interface — this is the fastest way to validate the tools work before building the web UI.

**Phase 2 — RCA reasoning layer**
- Add the Claude API integration: feed collected logs + context to Claude, ask for probable cause + recommended next steps, structured as a report.
- Define the manual-trigger workflow end-to-end: user asks "what broke between 2-3am on host X" → controller collects → Claude analyzes → report returned.

**Phase 3 — Web UI**
- Build the minimal FastAPI + frontend chat interface, surfacing tool calls, raw log excerpts, and the RCA report inline.
- Wire basic API-key/auth.

**Phase 4 — Guardrails hardening**
- Formalize the read-only command allowlist and host allowlist as config, not code.
- Add audit logging of every collection request (who, what host, what commands, when).
- Run `security-review` against the SSH controller and web auth before wider rollout.

**Phase 5 — Extend to Kubernetes**
- Add the k8s-table tools from `PLAN.md` (`kubectl get events`, `describe pod`, `logs -p`, `journalctl -u kubelet`, `crictl logs`, `/var/log/pods`, control-plane logs), reusing the same allowlist/audit pattern from Phase 4.

**Phase 6 — Extend to HA cluster (Pacemaker/Corosync)**
- Add `pcs status`/`crm_mon`, `/var/log/pacemaker/pacemaker.log`, `/var/log/cluster/corosync.log`, combined `journalctl -u pacemaker -u corosync`.

**Phase 7 — Proactive triggers (stretch)**
- Revisit alerting-integration or local-watcher auto-trigger now that manual flow is proven, per the earlier answer that this was deferred.

**Phase 8 — Containerize & deploy**
- Dockerize the web UI + MCP server + controller (using the `docker-expert` skill's hardening guidance).
- Write Kubernetes manifests to deploy the tool itself (using the `kubernetes` skill's conventions).
- Set up CI (GitHub Actions) for tests/lint/build, per `devops-engineer` skill guidance.

## Verification

- Phase 1: run the CLI against a real or test RHEL host, confirm each MCP tool returns expected log content and rejects out-of-allowlist hosts/commands.
- Phase 2: manually trigger an RCA on a known past incident (or a deliberately broken test VM) and check the report's accuracy against what actually happened.
- Phase 3: exercise the web UI in a browser for the golden path (ask a question → see tool calls → see report) and an auth-failure edge case.
- Phase 4: attempt a disallowed command/host through the API and confirm it's rejected and logged.
- Phase 5/6: repeat Phase 1's verification against a test k8s cluster and a test Pacemaker/Corosync cluster respectively.
- Phase 8: `docker build` + `docker run` locally, then deploy manifests to a test k8s namespace and confirm the web UI is reachable and functional end-to-end.
