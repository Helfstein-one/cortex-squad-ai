# ADR: [Concise Title]

## Status
[Proposed | Accepted | Rejected | Superseded]

## Context & Scope
- **Goal & Constraints**: [Problem statement, SLAs, target modules/tables]
- **Data Classification**: [Public | Internal | PII / Restricted (LGPD/GDPR)]
- **Verified Baseline**: [Tag existing symbols/files with `[VERIFIED: path:line]`]
- **Open Ambiguities / Assumptions**: [List any `[ASSUMPTION]` items and blast radius]

## Decision Drivers
- [Idempotency / Correctness / Latency / FinOps / Security / Testability]

## Options Considered
| Option | Summary | Key Pros | Key Cons / Risks | Rejection / Selection |
|---|---|---|---|---|
| `opt-1` | [Approach A] | [...] | [...] | [Selected / Rejected: reason] |
| `opt-2` | [Approach B] | [...] | [...] | [Selected / Rejected: reason] |

## Chosen Decision & Interface Contracts
- **Selected Option**: `[opt-id]` — [Architectural pattern and module placement]
- **Ports & Schemas**: [Define `typing.Protocol` signatures, Pydantic models, or SQL/Iceberg DDL + nullability]

## Failure Modes, Security & Observability
- **Failure Modes & Rollback**: [Retry/idempotency behavior, blast radius, exact rollback procedure]
- **Trust Boundaries & Compliance**: [IAM least privilege, PII tokenization/masking, secrets injection]
- **SLOs & Observability**: [Target latency/throughput, structured metrics/log keys]
- **FinOps Envelope**: [Expected compute/storage/shuffle/token footprint]

## Consequences
- **Positive**: [...]
- **Negative / Trade-offs**: [...]
- **Assumptions to Attack (`chaos-qa-critic`)**: [...]
