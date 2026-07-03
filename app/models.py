from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ConsentBasis(StrEnum):
    EXPLICIT_OPT_IN = "explicit_opt_in"
    REQUESTED_CALLBACK = "requested_callback"
    EXISTING_CUSTOMER = "existing_customer"
    TRANSACTIONAL_NOTICE = "transactional_notice"


class CallStatus(StrEnum):
    QUEUED = "queued"
    DISPATCHED = "dispatched"
    FAILED = "failed"


class CallRequest(BaseModel):
    phone_number: str = Field(description="E.164 format, for example +819012345678")
    recipient_name: str = Field(min_length=1, max_length=120)
    purpose: str = Field(min_length=1, max_length=500)
    consent_basis: ConsentBasis
    context: dict[str, Any] = Field(default_factory=dict)
    transfer_to: str | None = None

    @field_validator("phone_number", "transfer_to")
    @classmethod
    def strip_phone(cls, value: str | None) -> str | None:
        return value.strip() if value else value


class CallResponse(BaseModel):
    id: str
    status: CallStatus
    phone_masked: str
    room_name: str | None = None
    dispatch_id: str | None = None
    created_at: str
    policy_summary: str


class SuppressionRequest(BaseModel):
    phone_number: str
    reason: str = Field(default="recipient_opt_out", max_length=200)


class HealthResponse(BaseModel):
    status: str
    dry_run: bool
