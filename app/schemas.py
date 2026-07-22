from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class UserIdentityIn(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str = Field(min_length=1)
    arn: str | None = None


class CloudTrailEventIn(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    event_id: str = Field(alias="eventID", min_length=1, max_length=64)
    event_time: datetime = Field(alias="eventTime")
    event_source: str = Field(alias="eventSource", min_length=1, max_length=255)
    event_name: str = Field(alias="eventName", min_length=1, max_length=255)
    user_identity: UserIdentityIn = Field(alias="userIdentity")
    source_ip_address: str | None = Field(default=None, alias="sourceIPAddress")
    aws_region: str | None = Field(default=None, alias="awsRegion")
    response_elements: dict[str, Any] | None = Field(default=None, alias="responseElements")
    additional_event_data: dict[str, Any] | None = Field(
        default=None, alias="additionalEventData"
    )


class CloudTrailEnvelopeIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    records: list[CloudTrailEventIn] = Field(alias="Records", min_length=1, max_length=500)


class EventImportResult(BaseModel):
    total: int
    imported: int
    duplicates: int
    event_ids: list[str]


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    event_time: datetime
    event_source: str
    event_name: str
    identity_type: str
    actor_arn: str | None
    source_ip: str | None
    aws_region: str | None
    raw_event: dict[str, Any]
    created_at: datetime


class DetectionResponse(BaseModel):
    event_id: str
    matched: bool
    rule_id: str
    incident_id: str | None = None
    severity: str | None = None
    evidence: list[str] = Field(default_factory=list)


class IncidentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    incident_id: str
    event_id: str
    rule_id: str
    title: str
    severity: str
    evidence: list[str]
    status: str
    requires_human_approval: bool
    created_at: datetime


class HealthResponse(BaseModel):
    status: str
    environment: str

