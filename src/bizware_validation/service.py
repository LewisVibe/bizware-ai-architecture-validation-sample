from __future__ import annotations

import hashlib

from .ledger import InMemoryLedger
from .models import CoachingRequest, EvidenceItem, ProviderResult, ValidationOutcome
from .provider import CoachingProvider


class EvidenceStore:
    def __init__(self, items: list[EvidenceItem]) -> None:
        self._items = {item.evidence_id: item for item in items}

    def get(self, evidence_id: str) -> EvidenceItem | None:
        return self._items.get(evidence_id)


class ValidationService:
    POLICY_VERSION = "architecture-sample-v1"

    def __init__(
        self,
        provider: CoachingProvider,
        evidence_store: EvidenceStore,
        ledger: InMemoryLedger,
    ) -> None:
        self.provider = provider
        self.evidence_store = evidence_store
        self.ledger = ledger

    def validate(self, request: CoachingRequest) -> ValidationOutcome:
        key = self._idempotency_key(request)
        existing = self.ledger.get(key)

        if existing is not None:
            if existing.state == "completed" and existing.outcome is not None:
                return ValidationOutcome(
                    status="duplicate",
                    idempotency_key=key,
                    reasons=("already_completed",),
                    result=existing.outcome.result,
                )
            return ValidationOutcome(
                status="blocked",
                idempotency_key=key,
                reasons=(existing.state,),
            )

        if not self.ledger.claim(key):
            return ValidationOutcome(
                status="blocked",
                idempotency_key=key,
                reasons=("concurrent_claim",),
            )

        try:
            result = self.provider.generate(request)
            outcome = self._evaluate(request, result, key)
        except Exception as error:
            self.ledger.require_reconciliation(key, error)
            return ValidationOutcome(
                status="blocked",
                idempotency_key=key,
                reasons=(f"provider_failure:{type(error).__name__}",),
            )

        self.ledger.complete(key, outcome)
        return outcome

    def _evaluate(
        self,
        request: CoachingRequest,
        result: ProviderResult,
        key: str,
    ) -> ValidationOutcome:
        allowed = set(request.allowed_evidence_ids)
        referenced = set(result.evidence_ids)

        if not referenced:
            return ValidationOutcome(
                status="human_review",
                idempotency_key=key,
                reasons=("no_supporting_evidence",),
                result=result,
            )

        unapproved = referenced - allowed
        if unapproved:
            return ValidationOutcome(
                status="blocked",
                idempotency_key=key,
                reasons=(f"evidence_not_allowed:{','.join(sorted(unapproved))}",),
            )

        for evidence_id in sorted(referenced):
            item = self.evidence_store.get(evidence_id)
            if item is None:
                return ValidationOutcome(
                    status="blocked",
                    idempotency_key=key,
                    reasons=(f"evidence_missing:{evidence_id}",),
                )
            if item.tenant_id != request.tenant_id:
                return ValidationOutcome(
                    status="blocked",
                    idempotency_key=key,
                    reasons=(f"tenant_mismatch:{evidence_id}",),
                )

        review_reasons: list[str] = []
        if result.requires_human_review:
            review_reasons.append("provider_requested_review")
        if result.confidence < request.minimum_confidence:
            review_reasons.append("confidence_below_threshold")

        if review_reasons:
            return ValidationOutcome(
                status="human_review",
                idempotency_key=key,
                reasons=tuple(review_reasons),
                result=result,
            )

        return ValidationOutcome(
            status="accepted",
            idempotency_key=key,
            result=result,
        )

    @classmethod
    def _idempotency_key(cls, request: CoachingRequest) -> str:
        value = f"{request.tenant_id}:{request.request_id}:{cls.POLICY_VERSION}"
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]
