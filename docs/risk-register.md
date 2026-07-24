# Initial risk register

This is a starting point for validation, not a claim about Bizware's private implementation.

| Risk | Validation evidence | Likely treatment |
| --- | --- | --- |
| Model returns structurally valid but unsupported coaching | Verify every cited evidence ID against the allowed tenant-scoped set | Block unsupported evidence; route missing evidence to review |
| Duplicate request creates duplicate downstream work | Replay the same request and simulate overlapping claims | Deterministic key plus transactional claim |
| Provider timeout leaves outcome uncertain | Interrupt before and after the provider boundary | Persist `reconciliation_required`; do not retry blindly |
| Client data crosses tenant boundaries | Attempt a reference to evidence owned by another tenant | Tenant filter in retrieval and validation |
| Model or prompt change alters scoring | Run a fixed representative evaluation set by version | Versioned prompts/models and release thresholds |
| Context growth causes cost or latency spikes | Measure representative and worst-case payloads | Budget limits, retrieval filters and truncation policy |
| Logs expose private sales data | Inspect application, provider and infrastructure logs | Redaction, access control and retention limits |
| Provider cannot meet residency requirements | Confirm processing region, retention and subprocessors | Select compliant deployment or keep affected data out |
