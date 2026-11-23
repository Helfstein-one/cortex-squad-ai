# Production Readiness Checklist (Python Services & Adapters)

Run through every check before handing off Python implementation work to Phase 3 Quorum:

- [ ] **Hexagonal Boundaries**: Zero infrastructure/framework imports in `domain/`; Use Cases depend only on `typing.Protocol` ports.
- [ ] **Async & Timeouts**: Zero blocking I/O in `async def`; every external HTTP/DB/LLM/subprocess call has an explicit timeout and bounded retry policy.
- [ ] **Pydantic v2 Boundary Validation**: All untrusted inputs validated at inbound/outbound boundaries with explicit constraints and clear `4xx`/domain errors.
- [ ] **Error Mapping & Cleanup**: Adapter exceptions mapped cleanly to domain errors; resources/connections closed via context managers (`async with` / `with`).
- [ ] **OWASP & Injection Hygiene**: Zero hardcoded secrets, zero `shell=True`, zero SQL string interpolation, and validated filesystem paths.
- [ ] **Structured Observability**: Logs include correlation/mission ID, step, duration, and error code without emitting PII or credentials.
- [ ] **Protocol Fake & Edge Tests**: Unit tests exercise Use Cases via in-memory `Protocol` fakes covering empty inputs, timeouts, and error paths.
- [ ] **Static Gates**: `ruff check .`, `mypy --strict`, and `pytest -v` pass cleanly after the final edit.
