from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    event_source: Mapped[str] = mapped_column(String(255), index=True)
    event_name: Mapped[str] = mapped_column(String(255), index=True)
    identity_type: Mapped[str] = mapped_column(String(64), index=True)
    actor_arn: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_ip: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    aws_region: Mapped[str | None] = mapped_column(String(64), nullable=True)
    raw_event: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    incidents: Mapped[list["Incident"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (UniqueConstraint("event_id", "rule_id", name="uq_incident_event_rule"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    incident_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    event_id: Mapped[str] = mapped_column(
        ForeignKey("security_events.event_id", ondelete="CASCADE"), index=True
    )
    rule_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(32), index=True)
    evidence: Mapped[list[str]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    requires_human_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    event: Mapped[SecurityEvent] = relationship(back_populates="incidents")

