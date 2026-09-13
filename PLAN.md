Project Goal

The plan is to build a roadmap for a Linux log-analysis project. The system should let me query a live server to see what's currently happening on it, and when an issue occurs — after the system is back up — automatically collect the relevant logs for RCA: what caused the problem and what the recommended next steps are.

Key features

Expose the log-collection and analysis capabilities as MCP tools.
Allow interaction through a web browser prompt.
Make the AI proactive — able to use Claude or other LLMs to investigate and suggest fixes on its own.
Develop it as a proper, well-structured project with a friendly, Unix-like interface anyone on the team can access to troubleshoot.
Add guardrails and proper access restrictions on the server side when collecting data.
Deploy with Docker and Kubernetes.
Push everything to GitHub and treat it as a full AI project.




Standalone (RHEL/systemd)
Path / Command	What it tells you
journalctl -xe	Most recent errors with context — first stop
journalctl -b / -b -1	Current / previous boot logs
journalctl -u <svc> --since "1 hour ago"	Per-service failure timeline
/var/log/messages	General system/daemon messages
/var/log/secure	SSH, sudo, auth failures, logins
dmesg -T	Kernel: OOM-kills, disk/HW errors, driver issues
/var/log/audit/audit.log	SELinux denials (ausearch -m avc, aureport)
/var/log/cron	Cron/timer job runs
/var/log/dnf.log	Package installs/updates (correlate to breakage)
/var/log/httpd/ /var/log/nginx/	App/web layer errors
sar (sysstat, /var/log/sa/)	Historical CPU/mem/IO/net — perf RCA

Cluster

Kubernetes

Source	Use
kubectl get events -A --sort-by=.lastTimestamp	Cluster-wide recent failures
kubectl describe pod <p>	Scheduling, image pull, probe, OOM reasons
kubectl logs <p> [-p] [-c <ctr>]	App logs; -p = previous crashed instance
journalctl -u kubelet	Node agent — the #1 node-level RCA source
journalctl -u containerd / crictl logs	Runtime issues
/var/log/pods/, /var/log/containers/	On-node raw container logs
etcd / kube-apiserver logs (pods in kube-system or /var/log/)	Control-plane RCA



HA cluster (Pacemaker/Corosync — common on RHEL)

Source	Use
pcs status / crm_mon -1	Resource/node/quorum state
/var/log/pacemaker/pacemaker.log	Resource start/stop/failover, fencing
/var/log/cluster/corosync.log	Membership, quorum, split-brain
journalctl -u pacemaker -u corosync	Combined timeline


