from __future__ import annotations

import json
import os
from typing import Any

from sqlalchemy.orm import Session

from app.agent_policy import (
    AGENT_INSTRUCTIONS,
    AGENT_TOOLS,
    AgentConfigurationError,
    AgentStepLimitError,
    validate_agent_steps,
    validate_tool_arguments,
)
from app.models import AuditLog, Incident
from app.reporting import build_incident_report
from app.repositories import create_audit_log, get_event


def _dispatch_read_only_tool(
    session: Session,
    *,
    incident: Incident,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    if tool_name == "get_event_context":
        validate_tool_arguments(
            arguments, expected_key="event_id", expected_value=incident.event_id
        )
        event = get_event(session, incident.event_id)
        if event is None:
            raise LookupError("Incident event is missing")
        return {
            "untrusted_data": True,
            "event_id": event.event_id,
            "event_time": event.event_time.isoformat(),
            "event_source": event.event_source,
            "event_name": event.event_name,
            "identity_type": event.identity_type,
            "actor_arn": event.actor_arn,
            "source_ip": event.source_ip,
            "aws_region": event.aws_region,
            "raw_event": event.raw_event,
        }

    if tool_name == "get_incident_report":
        validate_tool_arguments(
            arguments,
            expected_key="incident_id",
            expected_value=incident.incident_id,
        )
        event = get_event(session, incident.event_id)
        if event is None:
            raise LookupError("Incident event is missing")
        report = build_incident_report(incident, event)
        return {
            "untrusted_data": True,
            "report": report.model_dump(mode="json"),
        }

    raise ValueError(f"Tool is not allow-listed: {tool_name}")


def execute_and_audit_tool(
    session: Session,
    *,
    incident: Incident,
    tool_name: str,
    raw_arguments: str,
) -> tuple[dict[str, Any], AuditLog]:
    try:
        parsed = json.loads(raw_arguments)
        if not isinstance(parsed, dict):
            raise ValueError("Tool arguments must be a JSON object")
        result = _dispatch_read_only_tool(
            session,
            incident=incident,
            tool_name=tool_name,
            arguments=parsed,
        )
        success = True
    except (json.JSONDecodeError, ValueError, LookupError) as error:
        parsed = {"raw_arguments": raw_arguments}
        result = {"error": str(error)}
        success = False

    audit = create_audit_log(
        session,
        incident_id=incident.incident_id,
        action_type="agent_tool_call",
        tool_name=tool_name,
        request_payload=parsed,
        response_payload=result,
        success=success,
    )
    return result, audit


async def run_security_analyst(
    session: Session,
    *,
    incident: Incident,
    model: str,
    max_steps: int,
    client: Any | None = None,
) -> tuple[str, list[AuditLog]]:
    validate_agent_steps(max_steps)

    if client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise AgentConfigurationError("OPENAI_API_KEY is not configured")
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key)

    input_items: list[Any] = [
        {
            "role": "user",
            "content": (
                f"Investigate incident {incident.incident_id}. Its associated "
                f"event ID is {incident.event_id}."
            ),
        }
    ]
    audit_items: list[AuditLog] = []

    for step in range(max_steps):
        response = await client.responses.create(
            model=model,
            instructions=AGENT_INSTRUCTIONS,
            input=input_items,
            tools=AGENT_TOOLS,
            tool_choice="required" if step == 0 else "auto",
            parallel_tool_calls=False,
            reasoning={"effort": "medium"},
            store=False,
        )
        input_items.extend(response.output)
        tool_calls = [
            item for item in response.output if item.type == "function_call"
        ]
        if not tool_calls:
            analysis = response.output_text.strip()
            if not analysis:
                raise AgentStepLimitError("Agent returned no final analysis")
            audit_items.append(
                create_audit_log(
                    session,
                    incident_id=incident.incident_id,
                    action_type="agent_completion",
                    tool_name=None,
                    request_payload={"model": model, "steps": step + 1},
                    response_payload={"analysis": analysis},
                    success=True,
                )
            )
            return analysis, audit_items

        for tool_call in tool_calls:
            result, audit = execute_and_audit_tool(
                session,
                incident=incident,
                tool_name=tool_call.name,
                raw_arguments=tool_call.arguments,
            )
            audit_items.append(audit)
            input_items.append(
                {
                    "type": "function_call_output",
                    "call_id": tool_call.call_id,
                    "output": json.dumps(result, ensure_ascii=False),
                }
            )

    audit_items.append(
        create_audit_log(
            session,
            incident_id=incident.incident_id,
            action_type="agent_step_limit",
            tool_name=None,
            request_payload={"model": model, "max_steps": max_steps},
            response_payload={"error": "Agent exceeded its configured step limit"},
            success=False,
        )
    )
    raise AgentStepLimitError("Agent exceeded its configured step limit")
