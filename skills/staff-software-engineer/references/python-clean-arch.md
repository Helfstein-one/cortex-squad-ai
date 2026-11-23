# Python Clean Architecture, Async & Security Patterns

Apply these patterns to all Python 3.11+ services, Use Cases, and Adapters.

## 1. Domain & Application Purity

- **Immutable Domain Models**: Use `@dataclass(frozen=True, slots=True)` or Pydantic `BaseModel` with `model_config = ConfigDict(frozen=True)` for entities and value objects.
- **Port Injection via Constructor**: Use Cases accept `typing.Protocol` abstractions in `__init__`; never instantiate concrete HTTP, DB, or LLM clients inside `domain/` or `application/`.
- **Strict Typing**: All signatures must pass `mypy --strict`. Use `StrEnum`, `NewType`, or typed DTOs over untyped `dict[str, Any]` inside Domain/Application.

## 2. Boundary Validation & Error Mapping

- **Pydantic v2 at Inbound Adapters**: Validate external JSON, CLI, HTTP, and MCP payloads at adapter boundaries (`model_validate`, strict field bounds, `extra="forbid"` where appropriate).
- **Domain Exception Mapping**: Catch transport/driver exceptions inside outbound adapters and re-raise explicit domain exceptions (`SkillNotFoundError`, `PersistenceError`, `ExternalTimeoutError`) with contextual metadata (never raw secrets).

## 3. Async Discipline & Bounded Resilience

- **No Blocking Calls on Event Loop**: Never call blocking `requests`, `time.sleep`, or heavy synchronous disk/CPU work inside `async def`; use native async drivers or `asyncio.to_thread` with bounded pools.
- **Explicit Timeouts & Bounded Concurrency**: Wrap external I/O with `asyncio.wait_for` / `asyncio.timeout`; bound fan-out with `asyncio.Semaphore` and `asyncio.TaskGroup`.
- **Idempotency & Retries**: Retry only idempotent operations on transient failures using bounded exponential backoff with jitter.

## 4. OWASP & Deterministic Testing

- **Input & Path Safety**: Reject path traversal (`Path.resolve()` containment checks), enforce parameterized SQL, avoid `shell=True`, and never use `eval`/`exec`/`pickle` on untrusted data.
- **Protocol Fake Testing**: Test Use Cases with lightweight in-memory `Protocol` fakes (zero live network/LLM dependencies) plus contract tests on adapters.
