import os
from pathlib import Path

import paramiko
import uvicorn
from fastapi import Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from rca_log_map.config import load_hosts
from rca_log_map.rca.agent import investigate as run_investigation
from rca_log_map.rca.schemas import InvestigationResult
from rca_log_map.web.auth import API_KEY_ENV_VAR, require_api_key

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="rca-log-map")


class InvestigateRequest(BaseModel):
    host: str
    question: str
    max_iterations: int = 6


@app.get("/api/hosts", dependencies=[Depends(require_api_key)])
def api_hosts() -> list[dict]:
    try:
        hosts = load_hosts()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [{"alias": alias, "hostname": host.hostname} for alias, host in hosts.items()]


@app.post("/api/investigate", dependencies=[Depends(require_api_key)])
def api_investigate(body: InvestigateRequest) -> InvestigationResult:
    try:
        return run_investigation(body.host, body.question, max_iterations=body.max_iterations)
    except (KeyError, ValueError, FileNotFoundError, OSError, paramiko.SSHException, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


def main() -> None:
    if not os.environ.get(API_KEY_ENV_VAR):
        raise SystemExit(f"{API_KEY_ENV_VAR} must be set to run the web UI")
    port = int(os.environ.get("RCA_WEB_PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
