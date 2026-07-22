from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from app.agent import execute_and_audit_tool, run_security_analyst
from app.db import Database
from app.detection import analyze_event_all
from app.models import Incident
from app.repositories import get_event, import_events, list_audit_logs
from app.schemas import CloudTrailEnvelopeIn


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class FakeResponses:
    def __init__(self, incident: Incident) -> None:
        self.incident = incident
        self.calls = 0

    async def create(self, **_: object) -> SimpleNamespace:
        self.calls += 1
        if self.calls == 1:
            output = [
                SimpleNamespace(
                    type="function_call",
                    name="get_event_context",
                    arguments=json.dumps({"event_id": self.incident.event_id}),
                    call_id="call-event",
                )
            ]
            return SimpleNamespace(output=output, output_text="")
        if self.calls == 2:
            output = [
                SimpleNamespace(
                    type="function_call",
                    name="get_incident_report",
                    arguments=json.dumps(
                        {"incident_id": self.incident.incident_id}
                    ),
                    call_id="call-report",
                )
            ]
            return SimpleNamespace(output=output, output_text="")
        return SimpleNamespace(
            output=[],
            output_text=(
                "Critical audit logging change confirmed by stored evidence. "
                "Restore logging after human approval."
            ),
        )


class FakeClient:
    def __init__(self, incident: Incident) -> None:
        self.responses = FakeResponses(incident)


def _database_with_incident() -> tuple[Database, int]:
    database = Database("sqlite:///:memory:")
    database.create_schema()
    session_generator = database.session()
    session = next(session_generator)

    payload = json.loads(
        (PROJECT_ROOT / "data" / "additional_security_events.json").read_text(
            encoding="utf-8"
        )
    )
    import_events(session, CloudTrailEnvelopeIn.model_validate(payload).records)
    event_id = "00000000-0000-4000-8000-000000000011"
    event = get_event(session, event_id)
    assert event is not None
    results = analyze_event_all(session, event)
    assert len(results) == 1
    incident = results[0][1]
    incident_primary_key = incident.id
    try:
        next(session_generator)
    except StopIteration:
        pass
    return database, incident_primary_key


def test_agent_uses_only_audited_read_only_tools() -> None:
    database, incident_primary_key = _database_with_incident()
    session = None
    try:
        session = database.session_factory()
        persisted = session.get(Incident, incident_primary_key)
        assert persisted is not None

        analysis, audit = asyncio.run(
            run_security_analyst(
                session,
                incident=persisted,
                model="test-model",
                max_steps=4,
                client=FakeClient(persisted),
            )
        )

        assert "human approval" in analysis
        assert [item.action_type for item in audit] == [
            "agent_tool_call",
            "agent_tool_call",
            "agent_completion",
        ]
        assert all(item.success for item in audit)
        assert len(list_audit_logs(session, persisted.incident_id)) == 3
    finally:
        if session is not None:
            session.close()
        database.dispose()


def test_tool_cannot_cross_the_incident_boundary() -> None:
    database, incident_primary_key = _database_with_incident()
    session = database.session_factory()
    try:
        persisted = session.get(Incident, incident_primary_key)
        assert persisted is not None
        result, audit = execute_and_audit_tool(
            session,
            incident=persisted,
            tool_name="get_event_context",
            raw_arguments=json.dumps({"event_id": "another-event"}),
        )

        assert "error" in result
        assert audit.success is False
    finally:
        session.close()
        database.dispose()
