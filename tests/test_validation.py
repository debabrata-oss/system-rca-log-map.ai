import pytest

from rca_log_map.controller.validation import (
    validate_boot_offset,
    validate_container_id,
    validate_day,
    validate_enum,
    validate_k8s_name,
    validate_lines,
    validate_since,
    validate_unit_name,
)


def test_validate_lines_default():
    assert validate_lines(None) == 200


def test_validate_lines_caps_at_hard_max():
    assert validate_lines(999_999) == 2000


def test_validate_lines_rejects_non_positive():
    with pytest.raises(ValueError):
        validate_lines(0)


def test_validate_lines_rejects_non_int():
    with pytest.raises(ValueError):
        validate_lines("1; cat /etc/shadow")


def test_validate_unit_name_appends_service_suffix():
    assert validate_unit_name("sshd") == "sshd.service"


def test_validate_unit_name_keeps_existing_suffix():
    assert validate_unit_name("nginx.service") == "nginx.service"


def test_validate_unit_name_rejects_injection():
    with pytest.raises(ValueError):
        validate_unit_name("sshd; rm -rf /")


def test_validate_unit_name_rejects_empty():
    with pytest.raises(ValueError):
        validate_unit_name("")


@pytest.mark.parametrize(
    "value",
    ["1 hour ago", "2 hours ago", "30 minutes ago", "today", "2024-01-02", "2024-01-02 10:00"],
)
def test_validate_since_accepts_known_forms(value):
    assert validate_since(value) == value


@pytest.mark.parametrize(
    "value",
    ["`reboot`", "$(reboot)", "1 hour ago; reboot", "next thursday", ""],
)
def test_validate_since_rejects_unknown_forms(value):
    with pytest.raises(ValueError):
        validate_since(value)


def test_validate_enum_accepts_known_choice():
    assert validate_enum("httpd", ("httpd", "nginx")) == "httpd"


def test_validate_enum_rejects_unknown_choice():
    with pytest.raises(ValueError):
        validate_enum("httpd; rm -rf /", ("httpd", "nginx"))


def test_validate_boot_offset_accepts_zero_and_minus_one():
    assert validate_boot_offset(0) == 0
    assert validate_boot_offset(-1) == -1


def test_validate_boot_offset_rejects_other_values():
    with pytest.raises(ValueError):
        validate_boot_offset(-2)


def test_validate_day_accepts_none_and_range():
    assert validate_day(None) is None
    assert validate_day(15) == 15


def test_validate_day_rejects_out_of_range():
    with pytest.raises(ValueError):
        validate_day(32)
    with pytest.raises(ValueError):
        validate_day(0)


def test_validate_container_id_accepts_hex():
    assert validate_container_id("a" * 12) == "a" * 12
    assert validate_container_id("0123456789abcdef") == "0123456789abcdef"


@pytest.mark.parametrize("value", ["", "short", "not-hex-at-all", "GHIJKL01", "abc; rm -rf /"])
def test_validate_container_id_rejects_invalid(value):
    with pytest.raises(ValueError):
        validate_container_id(value)


@pytest.mark.parametrize("value", ["web1", "my-pod-abc123", "a"])
def test_validate_k8s_name_accepts_valid_names(value):
    assert validate_k8s_name(value, "pod") == value


@pytest.mark.parametrize(
    "value", ["", "Web1", "-leading-hyphen", "trailing-hyphen-", "pod; rm -rf /", "a" * 254]
)
def test_validate_k8s_name_rejects_invalid_names(value):
    with pytest.raises(ValueError):
        validate_k8s_name(value, "pod")
