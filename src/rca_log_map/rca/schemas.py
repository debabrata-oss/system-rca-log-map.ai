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


class TranscriptEvent(BaseModel):
    type: Literal["tool_call", "tool_result"]
    name: str
    input: dict | None = None
    output: str | None = None


class InvestigationResult(BaseModel):
    report: RCAReport
    transcript: list[TranscriptEvent]
