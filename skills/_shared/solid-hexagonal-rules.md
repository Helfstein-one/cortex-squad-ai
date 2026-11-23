# Clean, Hexagonal, Data & Secure Coding Rules

All builders, conceptualizers, and critics enforce these invariants across Python services and data pipelines.

## 1. Hexagonal & SOLID Python Architecture

1. **Domain Layer (`domain/`)**:
   - Zero imports of external frameworks, LLM SDKs, ORMs, HTTP clients, Spark sessions, or filesystem I/O.
   - Model entities and value objects as immutable structures (`@dataclass(frozen=True)` or Pydantic `ConfigDict(frozen=True)`).
2. **Application Layer (`application/`)**:
   - Orchestrate workflows in single-responsibility Use Cases.
   - Depend exclusively on abstract `typing.Protocol` ports injected via `__init__`; never import concrete adapters.
3. **Adapters Layer (`adapters/`)**:
   - Isolate concrete I/O (databases, object storage, HTTP APIs, LLM providers, CLI, MCP).
   - Validate untrusted external payloads at the boundary and map provider exceptions to explicit domain exceptions.
4. **Strict Typing & Lint Hygiene**:
   - Full parameter and return type annotations on all functions/methods (`mypy --strict` compliant).
   - Pass project lint rules (`ruff check .`, Python 3.11+, max line length 100).

## 2. Data Pipeline Pure-Transform Separation

1. **Decouple Transforms from I/O**: Keep PySpark, SQL, and dbt transformation functions pure and deterministic (input DataFrames/tables -> transformed DataFrames/tables), isolated from `SparkSession` setup, secrets loading, and sink writes.
2. **Idempotency & Replay Safety**: Every sink write must be safely re-runnable (`MERGE INTO` with deterministic composite keys/watermarks or atomic partition overwrite). Never mutate caller-owned collections in place.
3. **Explicit Contracts**: Declare explicit schemas, nullability, primary-key invariants, and schema-evolution rules; never infer production schemas from untrusted raw files.

## 3. Secure Coding & Observability Baseline

1. **Zero Hardcoded Secrets**: Never embed API keys, tokens, passwords, private keys, or credentialed DSNs in code, YAML, SQL, or logs. Load via secrets/env ports and redact sensitive fields before logging.
2. **Injection Prevention**: Use parameterized queries / bound parameters for SQL and argument lists (`shell=False`) for subprocesses. Never interpolate untrusted input into SQL, shell commands, or dynamic `eval`/`exec`.
3. **Resilience & Bounded Execution**: Enforce explicit timeouts on all external/network calls, bounded retries with jitter on transient errors, and bounded concurrency (`asyncio.Semaphore` / `TaskGroup`).
4. **Structured Observability**: Emit structured logs (`mission_id`, `step`, `persona`, `duration_ms`, `status`, `error_code`) without logging raw PII or secrets.
