import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

DEFAULT_CONFIG_PATH = Path(
    os.environ.get("RCA_HOSTS_CONFIG", Path(__file__).parents[2] / "config" / "hosts.yaml")
)


class HostConfig(BaseModel):
    hostname: str
    port: int = 22
    username: str
    key_path: str = Field(alias="key_path")


def load_hosts(config_path: Path | None = None) -> dict[str, HostConfig]:
    path = config_path or DEFAULT_CONFIG_PATH
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
