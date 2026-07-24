from typing import Protocol

from .models import CoachingRequest, ProviderResult


class CoachingProvider(Protocol):
    """The only surface that needs to change when the LLM provider changes."""

    def generate(self, request: CoachingRequest) -> ProviderResult:
        ...
