import pytest

from rca_log_map.controller.commands import COMMAND_REGISTRY


def test_all_standalone_sources_registered():
    expected = {
        "journalctl_recent_errors",
        "journalctl_boot",
        "journalctl_service",
        "system_messages",
        "auth_log",
        "kernel_log",
        "selinux_denials",
        "cron_log",
        "package_log",
        "web_log",
        "sar_stats",
        "crictl_ps",
        "crictl_logs",
        "pcs_status",
        "crm_mon_status",
        "pacemaker_log",
        "corosync_log",
        "journalctl_ha_cluster",
    }
    assert expected == set(COMMAND_REGISTRY)


def test_journalctl_recent_errors_renders_expected_command():
    spec = COMMAND_REGISTRY["journalctl_recent_errors"]
    assert spec.render(lines=50) == "journalctl -xe -n 50 --no-pager"


def test_journalctl_service_renders_expected_command():
    spec = COMMAND_REGISTRY["journalctl_service"]
    cmd = spec.render(unit="sshd", since="2 hours ago", lines=100)
    assert cmd == 'journalctl -u sshd.service --since "2 hours ago" --no-pager -n 100'


def test_journalctl_service_rejects_unit_injection():
    spec = COMMAND_REGISTRY["journalctl_service"]
    with pytest.raises(ValueError):
        spec.render(unit="sshd; rm -rf /", since="1 hour ago", lines=100)


def test_journalctl_service_rejects_since_injection():
    spec = COMMAND_REGISTRY["journalctl_service"]
    with pytest.raises(ValueError):
        spec.render(unit="sshd", since="1 hour ago; reboot", lines=100)


def test_web_log_maps_server_to_correct_path():
    spec = COMMAND_REGISTRY["web_log"]
    assert spec.render(server="nginx", lines=20) == "tail -n 20 /var/log/nginx/error.log"
    assert spec.render(server="httpd", lines=20) == "tail -n 20 /var/log/httpd/error_log"


def test_web_log_rejects_unknown_server():
    spec = COMMAND_REGISTRY["web_log"]
    with pytest.raises(ValueError):
        spec.render(server="apache", lines=20)


def test_sar_stats_default_and_day():
    spec = COMMAND_REGISTRY["sar_stats"]
    assert spec.render() == "sar"
    assert spec.render(day=5) == "sar -f /var/log/sa/sa05"


def test_lines_param_is_clamped_not_injected():
    spec = COMMAND_REGISTRY["system_messages"]
    with pytest.raises(ValueError):
        spec.render(lines="1; cat /etc/shadow")


def test_crictl_ps_renders_expected_command():
    spec = COMMAND_REGISTRY["crictl_ps"]
    assert spec.render() == "crictl ps -a"


def test_crictl_logs_renders_expected_command():
    spec = COMMAND_REGISTRY["crictl_logs"]
    cid = "a" * 12
    assert spec.render(container_id=cid, lines=50) == f"crictl logs --tail 50 {cid}"
    assert spec.render(container_id=cid, lines=50, previous=True) == f"crictl logs --tail 50 -p {cid}"


def test_crictl_logs_rejects_bad_container_id():
    spec = COMMAND_REGISTRY["crictl_logs"]
    with pytest.raises(ValueError):
        spec.render(container_id="abc; rm -rf /", lines=50)


def test_pcs_status_renders_expected_command():
    assert COMMAND_REGISTRY["pcs_status"].render() == "pcs status"


def test_crm_mon_status_renders_expected_command():
    assert COMMAND_REGISTRY["crm_mon_status"].render() == "crm_mon -1"


def test_pacemaker_log_renders_expected_command():
    spec = COMMAND_REGISTRY["pacemaker_log"]
    assert spec.render(lines=50) == "tail -n 50 /var/log/pacemaker/pacemaker.log"


def test_corosync_log_renders_expected_command():
    spec = COMMAND_REGISTRY["corosync_log"]
    assert spec.render(lines=50) == "tail -n 50 /var/log/cluster/corosync.log"


def test_journalctl_ha_cluster_renders_expected_command():
    spec = COMMAND_REGISTRY["journalctl_ha_cluster"]
    cmd = spec.render(since="2 hours ago", lines=100)
    assert cmd == 'journalctl -u pacemaker -u corosync --since "2 hours ago" --no-pager -n 100'


def test_journalctl_ha_cluster_rejects_since_injection():
    spec = COMMAND_REGISTRY["journalctl_ha_cluster"]
    with pytest.raises(ValueError):
        spec.render(since="1 hour ago; reboot")
