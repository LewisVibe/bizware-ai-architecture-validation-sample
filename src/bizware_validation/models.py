from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EvidenceItem(StrictModel):
    evidence_id: str
    tenant_id: str
    content: str

    @field_validator("evidence_id", "tenant_id", "content")
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value:
            raise ValueError("value must not be blank")
        return value


class CoachingRequest(StrictModel):
    tenant_id: str
    request_id: str
    rep_message: str
    allowed_evidence_ids: tuple[str, ...] = ()
    minimum_confidence: float = Field(default=0.78, ge=0, le=1)

    @field_validator("tenant_id", "request_id", "rep_message")
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value:
            raise ValueError("value must not be blank")
        return value


class ProviderResult(StrictModel):
    answer: str
    coaching_action: str
    evidence_ids: tuple[str, ...]
    confidence: float = Field(ge=0, le=1)
    requires_human_review: bool = False
    model_version: str

    @field_validator("answer", "coaching_action", "model_version")
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value:
            raise ValueError("value must not be blank")
        return value


class ValidationOutcome(StrictModel):
    status: Literal["accepted", "human_review", "blocked", "duplicate"]
    idempotency_key: str
    reasons: tuple[str, ...] = ()
    result: ProviderResult | None = None
