from dataclasses import dataclass
from typing import Literal

from .models import ValidationOutcome


LedgerState = Literal["claimed", "completed", "reconciliation_required"]


@dataclass(frozen=True)
class LedgerRecord:
    state: LedgerState
    outcome: ValidationOutcome | None = None
    error_type: str | None = None


class InMemoryLedger:
    """Small stand-in for a transactional production ledger."""

    def __init__(self) -> None:
        self._records: dict[str, LedgerRecord] = {}

    def get(self, key: str) -> LedgerRecord | None:
        return self._records.get(key)

    def claim(self, key: str) -> bool:
        if key in self._records:
            return False
        self._records[key] = LedgerRecord(state="claimed")
        return True

    def complete(self, key: str, outcome: ValidationOutcome) -> None:
        self._records[key] = LedgerRecord(state="completed", outcome=outcome)

    def require_reconciliation(self, key: str, error: Exception) -> None:
        self._records[key] = LedgerRecord(
            state="reconciliation_required",
            error_type=type(error).__name__,
        )
