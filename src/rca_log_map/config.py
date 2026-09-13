import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

DEFAULT_HOSTS_CONFIG_PATH = "config/hosts.yaml"
DEFAULT_CLUSTERS_CONFIG_PATH = "config/clusters.yaml"


class HostConfig(BaseModel):
    hostname: str
    port: int = 22
    username: str
    key_path: str = Field(alias="key_path")
    allowed_sources: list[str] | None = None

    def is_source_allowed(self, command_name: str) -> bool:
        return self.allowed_sources is None or command_name in self.allowed_sources


def load_hosts(config_path: Path | None = None) -> dict[str, HostConfig]:
    path = config_path or Path(os.environ.get("RCA_HOSTS_CONFIG", DEFAULT_HOSTS_CONFIG_PATH))
    if not path.exists():
        raise FileNotFoundError(
            f"Host inventory not found at {path}. Copy config/hosts.example.yaml to "
            "config/hosts.yaml and fill in your hosts."
        )
    data = yaml.safe_load(path.read_text()) or {}
    hosts = data.get("hosts") or {}
    return {alias: HostConfig(**fields) for alias, fields in hosts.items()}


def get_host(alias: str, config_path: Path | None = None) -> HostConfig:
    hosts = load_hosts(config_path)
    if alias not in hosts:
        raise KeyError(
            f"Unknown host alias {alias!r}. Known hosts: {sorted(hosts) or '(none configured)'}"
        )
    return hosts[alias]


class ClusterConfig(BaseModel):
    kubeconfig_path: str
    context: str | None = None
    allowed_sources: list[str] | None = None

    def is_source_allowed(self, command_name: str) -> bool:
        return self.allowed_sources is None or command_name in self.allowed_sources


def load_clusters(config_path: Path | None = None) -> dict[str, ClusterConfig]:
    path = config_path or Path(os.environ.get("RCA_CLUSTERS_CONFIG", DEFAULT_CLUSTERS_CONFIG_PATH))
    if not path.exists():
        raise FileNotFoundError(
            f"Cluster inventory not found at {path}. Copy config/clusters.example.yaml to "
            "config/clusters.yaml and fill in your clusters."
        )
    data = yaml.safe_load(path.read_text()) or {}
    clusters = data.get("clusters") or {}
    return {alias: ClusterConfig(**fields) for alias, fields in clusters.items()}


def get_cluster(alias: str, config_path: Path | None = None) -> ClusterConfig:
    clusters = load_clusters(config_path)
    if alias not in clusters:
        raise KeyError(
            f"Unknown cluster alias {alias!r}. Known clusters: {sorted(clusters) or '(none configured)'}"
        )
    return clusters[alias]
