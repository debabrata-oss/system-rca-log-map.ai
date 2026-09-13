import re

UNIT_NAME_RE = re.compile(r"^[A-Za-z0-9_.@-]+$")
SINCE_RELATIVE_RE = re.compile(r"^\d+ (minute|minutes|hour|hours|day|days) ago$")
SINCE_ABSOLUTE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}( \d{2}:\d{2}(:\d{2})?)?$")
SINCE_KEYWORDS = {"today", "yesterday"}
CONTAINER_ID_RE = re.compile(r"^[a-f0-9]{8,64}$")
K8S_NAME_RE = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")


def validate_lines(value: int, default: int = 200, hard_max: int = 2000) -> int:
    if value is None:
        return default
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"lines must be an integer, got {value!r}")
    if value <= 0:
        raise ValueError("lines must be a positive integer")
    return min(value, hard_max)


def validate_unit_name(value: str) -> str:
    if not value or not UNIT_NAME_RE.match(value):
        raise ValueError(f"invalid systemd unit name: {value!r}")
    if "." not in value:
        value = f"{value}.service"
    return value


def validate_since(value: str) -> str:
    if not value:
        raise ValueError("since must not be empty")
    if value in SINCE_KEYWORDS:
        return value
    if SINCE_RELATIVE_RE.match(value) or SINCE_ABSOLUTE_RE.match(value):
        return value
    raise ValueError(
        f"invalid since expression: {value!r} "
        "(expected e.g. '2 hours ago', 'today', or 'YYYY-MM-DD [HH:MM[:SS]]')"
    )


def validate_enum(value: str, choices: tuple[str, ...]) -> str:
    if value not in choices:
        raise ValueError(f"invalid value {value!r}, expected one of {choices}")
    return value


def validate_boot_offset(value: int) -> int:
    if value not in (0, -1):
        raise ValueError(f"boot_offset must be 0 (current) or -1 (previous), got {value!r}")
    return value


def validate_day(value: int | None) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or not (1 <= value <= 31):
        raise ValueError(f"day must be an integer between 1 and 31, got {value!r}")
    return value


def validate_container_id(value: str) -> str:
    if not value or not CONTAINER_ID_RE.match(value):
        raise ValueError(f"invalid container id: {value!r}")
    return value


def validate_k8s_name(value: str, field: str) -> str:
    if not value or len(value) > 253 or not K8S_NAME_RE.match(value):
        raise ValueError(f"invalid {field}: {value!r}")
    return value
