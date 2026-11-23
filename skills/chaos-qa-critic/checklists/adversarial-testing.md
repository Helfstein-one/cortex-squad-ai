# Adversarial & Chaos Testing Checklist

Verify every builder submission against these failure classes before granting Quorum approval:

- [ ] **Null, Empty & Boundary Inputs**: Tested `None`, `""`, `[]`, `{}`, zero, negative values, and max-length payloads without unhandled exceptions.
- [ ] **Hot-Key Skew & Cardinality Spikes**: Verified joins, aggregations, and caches do not OOM or stall when a single key dominates (>50% of records).
- [ ] **Out-of-Order & Late-Arriving Events**: Verified timestamps arriving out of sequence or past watermarks do not overwrite newer state or drop valid rows.
- [ ] **Schema Drift & Type Coercion**: Verified unexpected columns, missing optional fields, and malformed types fail loudly at the boundary rather than corrupting sinks.
- [ ] **Duplicate & Replay Idempotency**: Re-running the same batch, event, or API call produces identical final state with zero duplicate records.
- [ ] **Concurrency, Timeouts & Partial Failures**: Verified external calls enforce timeouts, bounded concurrency, and safe cleanup on partial failures/crashes.
- [ ] **Security Injection Probes**: Tested SQL/path-traversal/command-injection strings and oversized payloads against boundary validators.
- [ ] **Mutation Probe Verification**: Exercised pipeline/service parsers against `scripts/mutation_probe.py` outputs (`nulls`, `skew`, `out-of-order`, `schema-drift`, `duplicates`).
