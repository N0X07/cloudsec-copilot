from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Incident, SecurityEvent
from app.schemas import CloudTrailEventIn


def import_events(
    session: Session, events: Iterable[CloudTrailEventIn]
) -> tuple[list[str], int]:
    imported_ids: list[str] = []
    duplicate_count = 0
    seen_in_payload: set[str] = set()

    for event in events:
        if event.event_id in seen_in_payload:
            duplicate_count += 1
            continue
        seen_in_payload.add(event.event_id)

        existing = session.scalar(
            select(SecurityEvent.id).where(SecurityEvent.event_id == event.event_id)
        )
        if existing is not None:
            duplicate_count += 1
            continue

        session.add(
            SecurityEvent(
                event_id=event.event_id,
                event_time=event.event_time,
                event_source=event.event_source,
                event_name=event.event_name,
                identity_type=event.user_identity.type,
                actor_arn=event.user_identity.arn,
                source_ip=event.source_ip_address,
                aws_region=event.aws_region,
                raw_event=event.model_dump(mode="json", by_alias=True),
            )
        )
        imported_ids.append(event.event_id)

    session.commit()
    return imported_ids, duplicate_count


def get_event(session: Session, event_id: str) -> SecurityEvent | None:
    return session.scalar(select(SecurityEvent).where(SecurityEvent.event_id == event_id))


def list_events(session: Session, *, offset: int, limit: int) -> list[SecurityEvent]:
    statement = (
        select(SecurityEvent)
        .order_by(SecurityEvent.event_time, SecurityEvent.event_id)
        .offset(offset)
        .limit(limit)
    )
    return list(session.scalars(statement))


def get_incident_for_rule(
    session: Session, *, event_id: str, rule_id: str
) -> Incident | None:
    return session.scalar(
        select(Incident).where(
            Incident.event_id == event_id,
            Incident.rule_id == rule_id,
        )
    )


def list_incidents(session: Session, *, offset: int, limit: int) -> list[Incident]:
    statement = (
        select(Incident)
        .order_by(Incident.created_at, Incident.incident_id)
        .offset(offset)
        .limit(limit)
    )
    return list(session.scalars(statement))


def get_incident(session: Session, incident_id: str) -> Incident | None:
    return session.scalar(
        select(Incident).where(Incident.incident_id == incident_id)
    )
