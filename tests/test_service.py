import pytest
from pydantic import ValidationError

from bizware_validation import (
    CoachingRequest,
    EvidenceItem,
    EvidenceStore,
    InMemoryLedger,
    ProviderResult,
    ValidationService,
)


class StubProvider:
    def __init__(
        self,
        result: ProviderResult | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.calls = 0

    def generate(self, request: CoachingRequest) -> ProviderResult:
        self.calls += 1
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


@pytest.fixture
def evidence_store() -> EvidenceStore:
    return EvidenceStore(
        [
            EvidenceItem(
                evidence_id="offer-1",
                tenant_id="tenant-a",
                content="The annual plan includes onboarding.",
            ),
            EvidenceItem(
                evidence_id="objection-1",
                tenant_id="tenant-a",
                content="Approved response to a pricing objection.",
            ),
            EvidenceItem(
                evidence_id="private-b",
                tenant_id="tenant-b",
                content="Evidence belonging to a different tenant.",
            ),
        ]
    )


def request(**changes: object) -> CoachingRequest:
    values: dict[str, object] = {
        "tenant_id": "tenant-a",
        "request_id": "req-001",
        "rep_message": "How should I handle this pricing objection?",
        "allowed_evidence_ids": ("offer-1", "objection-1"),
        "minimum_confidence": 0.78,
    }
    values.update(changes)
    return CoachingRequest.model_validate(values)


def result(**changes: object) -> ProviderResult:
    values: dict[str, object] = {
        "answer": "Acknowledge the concern and connect price to onboarding value.",
        "coaching_action": "Practise the approved pricing response.",
        "evidence_ids": ("offer-1", "objection-1"),
        "confidence": 0.91,
        "requires_human_review": False,
        "model_version": "stub-1",
    }
    values.update(changes)
    return ProviderResult.model_validate(values)


def service(
    evidence_store: EvidenceStore,
    provider: StubProvider,
    ledger: InMemoryLedger | None = None,
) -> ValidationService:
    return ValidationService(provider, evidence_store, ledger or InMemoryLedger())


def test_accepts_supported_high_confidence_result(evidence_store: EvidenceStore) -> None:
    outcome = service(evidence_store, StubProvider(result())).validate(request())

    assert outcome.status == "accepted"
    assert outcome.reasons == ()


def test_low_confidence_routes_to_human_review(evidence_store: EvidenceStore) -> None:
    outcome = service(
        evidence_store,
        StubProvider(result(confidence=0.45)),
    ).validate(request())

    assert outcome.status == "human_review"
    assert "confidence_below_threshold" in outcome.reasons


def test_provider_can_request_human_review(evidence_store: EvidenceStore) -> None:
    outcome = service(
        evidence_store,
        StubProvider(result(requires_human_review=True)),
    ).validate(request())

    assert outcome.status == "human_review"
    assert "provider_requested_review" in outcome.reasons


def test_missing_evidence_routes_to_human_review(evidence_store: EvidenceStore) -> None:
    outcome = service(
        evidence_store,
        StubProvider(result(evidence_ids=())),
    ).validate(request())

    assert outcome.status == "human_review"
    assert outcome.reasons == ("no_supporting_evidence",)


def test_unapproved_evidence_is_blocked(evidence_store: EvidenceStore) -> None:
    outcome = service(
        evidence_store,
        StubProvider(result(evidence_ids=("offer-1", "not-allowed"))),
    ).validate(request())

    assert outcome.status == "blocked"
    assert outcome.reasons == ("evidence_not_allowed:not-allowed",)


def test_cross_tenant_evidence_is_blocked(evidence_store: EvidenceStore) -> None:
    outcome = service(
        evidence_store,
        StubProvider(result(evidence_ids=("private-b",))),
    ).validate(request(allowed_evidence_ids=("private-b",)))

    assert outcome.status == "blocked"
    assert outcome.reasons == ("tenant_mismatch:private-b",)


def test_duplicate_request_does_not_call_provider_twice(
    evidence_store: EvidenceStore,
) -> None:
    provider = StubProvider(result())
    validator = service(evidence_store, provider)

    first = validator.validate(request())
    second = validator.validate(request())

    assert first.status == "accepted"
    assert second.status == "duplicate"
    assert first.idempotency_key == second.idempotency_key
    assert provider.calls == 1


def test_provider_failure_requires_reconciliation_before_retry(
    evidence_store: EvidenceStore,
) -> None:
    provider = StubProvider(error=TimeoutError("provider timed out"))
    validator = service(evidence_store, provider)

    first = validator.validate(request())
    second = validator.validate(request())

    assert first.status == "blocked"
    assert first.reasons == ("provider_failure:TimeoutError",)
    assert second.reasons == ("reconciliation_required",)
    assert provider.calls == 1


def test_idempotency_key_is_tenant_scoped(evidence_store: EvidenceStore) -> None:
    provider_a = StubProvider(result())
    provider_b = StubProvider(result(evidence_ids=("private-b",)))

    outcome_a = service(evidence_store, provider_a).validate(request())
    outcome_b = service(evidence_store, provider_b).validate(
        request(tenant_id="tenant-b", allowed_evidence_ids=("private-b",))
    )

    assert outcome_a.idempotency_key != outcome_b.idempotency_key


def test_provider_result_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        ProviderResult.model_validate(
            {
                "answer": "Answer",
                "coaching_action": "Action",
                "evidence_ids": ("offer-1",),
                "confidence": 0.9,
                "requires_human_review": False,
                "model_version": "stub-1",
                "unexpected": "quietly accepting this would hide a contract change",
            }
        )


def test_request_rejects_blank_identifiers() -> None:
    with pytest.raises(ValidationError):
        request(request_id="   ")
