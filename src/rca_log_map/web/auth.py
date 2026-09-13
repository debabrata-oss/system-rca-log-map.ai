import os
import secrets

from fastapi import Header, HTTPException

API_KEY_ENV_VAR = "RCA_WEB_API_KEY"


def require_api_key(x_api_key: str = Header(default="")) -> None:
    expected = os.environ.get(API_KEY_ENV_VAR)
    if not expected:
        raise RuntimeError(f"{API_KEY_ENV_VAR} must be set to run the web UI")
    if not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="invalid or missing API key")
