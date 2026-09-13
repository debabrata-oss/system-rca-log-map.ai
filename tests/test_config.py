from rca_log_map.config import HostConfig

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
