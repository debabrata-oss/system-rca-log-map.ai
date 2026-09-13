import os

import anthropic
import paramiko

from rca_log_map.config import get_host
from rca_log_map.rca.schemas import InvestigationResult, RCAReport, TranscriptEvent
from rca_log_map.rca.tool_specs import LOG_TOOL_DISPATCH, LOG_TOOL_SCHEMAS, SUBMIT_REPORT_TOOL

DEFAULT_MODEL = os.environ.get("RCA_ANTHROPIC_MODEL", "claude-sonnet-5")
MAX_TOKENS = 2048

SYSTEM_PROMPT_TEMPLATE = """\
You are investigating a Linux system incident on host "{host}".
You have read-only log-collection tools available. Call as many of them as you
need -- and no more -- to form a confident root-cause hypothesis, then call
submit_rca_report exactly once with your conclusion. Do not guess at a root
cause without checking at least one relevant log source first.
"""


def investigate(host: str, question: str, max_iterations: int = 6) -> InvestigationResult:
    get_host(host)  # fail fast: unknown host raises before any API call

    client = anthropic.Anthropic()
    messages: list[dict] = [{"role": "user", "content": question}]
    tools_used: list[str] = []
    transcript: list[TranscriptEvent] = []
    tools = [*LOG_TOOL_SCHEMAS, SUBMIT_REPORT_TOOL]

    for iteration in range(max_iterations):
        forced_final = iteration == max_iterations - 1
        response = client.messages.create(
            model=DEFAULT_MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT_TEMPLATE.format(host=host),
            messages=messages,
            tools=tools,
            tool_choice=(
                {"type": "tool", "name": "submit_rca_report"} if forced_final else {"type": "auto"}
            ),
        )
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            if block.name == "submit_rca_report":
                report = RCAReport(host=host, tools_used=tools_used, **block.input)
                return InvestigationResult(report=report, transcript=transcript)

            tools_used.append(block.name)
            transcript.append(TranscriptEvent(type="tool_call", name=block.name, input=block.input))
            try:
                output = LOG_TOOL_DISPATCH[block.name](host=host, **block.input)
            except (KeyError, ValueError, PermissionError, OSError, paramiko.SSHException) as exc:
                output = f"Error: {exc}"
            transcript.append(TranscriptEvent(type="tool_result", name=block.name, output=output))
            tool_results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": output}
            )

        if tool_results:
            messages.append({"role": "user", "content": tool_results})

    raise RuntimeError("investigation did not produce a report within max_iterations")
