# ADR Review Checklist

Verify every Architecture Decision Record against these gates before approving Phase 1 Conception:

- [ ] **Phase 0 Ambiguity Gate**: Are requirements, SLAs, data classification, and non-blocking assumptions explicitly stated?
- [ ] **Alternatives & Rejection Rationale**: Were at least 2 genuinely distinct options evaluated with explicit reasons for rejecting non-selected options?
- [ ] **SRP & Hexagonal Isolation**: Is the Domain layer free of external SDK, ORM, SparkSession, HTTP, and filesystem imports?
- [ ] **Typed Interface Contracts**: Are `typing.Protocol` ports, DDL/Iceberg schemas, nullability, and schema-evolution rules explicitly defined?
- [ ] **Idempotency & Failure Modes**: Are retries, duplicate events, partial failures, blast radius, and rollback steps specified?
- [ ] **Security & Trust Boundaries**: Are authentication/authorization boundaries, IAM least privilege, PII handling, and zero-hardcoded-secrets rules addressed?
- [ ] **Observability & SLOs**: Are latency/throughput targets, structured log fields, and health/error signals defined?
- [ ] **FinOps Envelope**: Are compute, storage, shuffle/I/O, and LLM token cost impacts bounded?
- [ ] **Grounding**: Are all referenced files, symbols, and constraints tagged `[VERIFIED: ...]` or `[ASSUMPTION]`?
