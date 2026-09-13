import os
import secrets

from fastapi import Header, HTTPException

API_KEY_ENV_VAR = "RCA_WEB_API_KEY"


def _expected_key() -> str:
    expected = os.environ.get(API_KEY_ENV_VAR)
    if not expected:
        raise RuntimeError(f"{API_KEY_ENV_VAR} must be set to run the web UI")
    return expected


def require_api_key(x_api_key: str = Header(default="")) -> None:
    if not secrets.compare_digest(x_api_key, _expected_key()):
        raise HTTPException(status_code=401, detail="invalid or missing API key")


def require_webhook_key(x_api_key: str = Header(default=""), api_key: str = "") -> None:
    expected = _expected_key()
    if secrets.compare_digest(x_api_key, expected) or secrets.compare_digest(api_key, expected):
        return
    raise HTTPException(status_code=401, detail="invalid or missing API key")
