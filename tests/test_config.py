from rca_log_map.config import HostConfig, load_hosts

BASE = {"hostname": "10.0.0.1", "port": 22, "username": "rca-svc", "key_path": "/fake/key"}


def test_is_source_allowed_defaults_to_all_when_unset():
    host = HostConfig(**BASE)
    assert host.is_source_allowed("journalctl_recent_errors")
    assert host.is_source_allowed("sar_stats")


def test_is_source_allowed_respects_allowlist():
    host = HostConfig(**BASE, allowed_sources=["journalctl_recent_errors", "system_messages"])
    assert host.is_source_allowed("journalctl_recent_errors")
    assert host.is_source_allowed("system_messages")
    assert not host.is_source_allowed("sar_stats")


def test_is_source_allowed_empty_list_denies_everything():
    host = HostConfig(**BASE, allowed_sources=[])
    assert not host.is_source_allowed("journalctl_recent_errors")


def test_load_hosts_default_path_is_cwd_relative_not_package_relative(tmp_path, monkeypatch):
    # Regression: the default used to be derived from config.py's own __file__
    # location, which only worked for an editable install run from the repo
    # root -- it silently pointed at a nonsense path once installed normally
    # (e.g. in a Docker image), even though RCA_HOSTS_CONFIG was unset.
    monkeypatch.delenv("RCA_HOSTS_CONFIG", raising=False)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "hosts.yaml").write_text(
        "hosts:\n  web1:\n    hostname: 10.0.0.1\n    username: rca-svc\n    key_path: /fake/key\n"
    )
    hosts = load_hosts()
    assert "web1" in hosts
