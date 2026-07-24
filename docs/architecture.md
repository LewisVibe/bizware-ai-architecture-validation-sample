# Architecture note

The sample keeps model-provider code separate from business validation. A provider swap should change the adapter, not the evidence, confidence, tenancy, or idempotency rules.

```mermaid
sequenceDiagram
    participant Client
    participant Validator
    participant Ledger
    participant Provider
    participant Evidence

    Client->>Validator: CoachingRequest
    Validator->>Ledger: claim(tenant, request, policy)
    alt already completed
        Ledger-->>Validator: completed result
        Validator-->>Client: duplicate
    else uncertain prior attempt
        Ledger-->>Validator: reconciliation_required
        Validator-->>Client: blocked
    else new request
        Ledger-->>Validator: claimed
        Validator->>Provider: generate(request)
        Provider-->>Validator: strict ProviderResult
        Validator->>Evidence: verify allowed IDs and tenant
        alt invalid evidence
            Validator->>Ledger: complete(blocked)
            Validator-->>Client: blocked
        else low confidence
            Validator->>Ledger: complete(human_review)
            Validator-->>Client: human_review
        else valid result
            Validator->>Ledger: complete(accepted)
            Validator-->>Client: accepted
        end
    end
```

## Production substitutions

| Sample component | Production concern |
| --- | --- |
| `StubProvider` | Selected provider SDK, timeout budget, model and prompt version |
| `InMemoryLedger` | Transactional database, leases, retention and audit access |
| `EvidenceStore` | Authorised retrieval layer with tenant-scoped queries |
| Pydantic schemas | Versioned API contracts and compatibility tests |
| Return value only | Explicit downstream action with its own idempotency boundary |
