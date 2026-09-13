from typing import Literal

from pydantic import BaseModel


class RCAReport(BaseModel):
    host: str
    summary: str
    likely_root_cause: str
    confidence: Literal["low", "medium", "high"]
    evidence: list[str]
    recommended_actions: list[str]
    tools_used: list[str]
