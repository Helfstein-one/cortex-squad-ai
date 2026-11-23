# CoALA Cognitive & Grounding Protocol

All personas must execute this reflective loop before proposing designs, mutating files, or issuing quorum verdicts.

## Phase 0: Scope & Ambiguity Gate

1. Verify the mission goal, target paths, SLAs, runtime constraints, and data sensitivity classification (`public`, `internal`, `pii/restricted`).
2. Identify missing contracts or conflicting requirements **before** generating code or ADRs.
3. If proceeding requires guessing a high-blast-radius decision (schema breaking change, auth boundary, data retention, destructive migration):
   - Surface the gap in `blocking_ambiguities` (portable handoff) or `assumptions_to_attack` (runtime JSON).
   - State explicit default assumptions and blast radius if non-blocking.

## Phase 1: Retrieval & Episodic Root-Cause Check

1. **Read Before Referencing**: Inspect existing files, schemas, ports, and tests via `ReadOnlyWorkspacePort` before citing any symbol, column, or file path.
2. **Episodic Memory Audit**: Review all prior `EpisodicEntry` items (`failure_signature`, `root_cause`, `remediation_hint`) and harness logs.
3. **No Repeat Failures**: Explicitly rule out any strategy whose root cause matches a previous failure unless the underlying defect is directly fixed.

## Phase 2–4: Proposal -> Evaluation -> Selection

1. **Proposal**: Formulate `2` to `max_deliberation_options` (default `3`) genuinely distinct approaches (different algorithms, data layouts, or architectural boundaries — not trivial parameter tweaks).
2. **Evaluation**: Score each option across explicit trade-off axes:
   - **Idempotency & Correctness**: Safe under retries, replays, nulls, and partial failures.
   - **Performance & Cost**: I/O volume, shuffle/spill risk, latency, compute/token cost.
   - **Simplicity & Modularity**: Minimal surface area, Hexagonal/SOLID decoupling, zero domain leakage.
   - **Testability & Security**: Deterministic local verification, input validation, zero secret/PII exposure.
3. **Selection**: Pick the strongest option and document concrete rejection reasons for discarded alternatives.

## Phase 5: Execution & Grounded Verification

1. Emit scoped, typed modifications or evidence-backed verdicts aligned with `handoff-contract.md`.
2. Execute deterministic checks (`pytest`, `ruff`, `mypy --strict`, `explain_plan_check.py`, `mutation_probe.py`) via `SandboxExecutorPort` when permitted by your role.
3. **Grounding & Anti-Hallucination Rule**:
   - Tag verified claims with `[VERIFIED: <file:line|command>]`.
   - Tag unverified premises with `[ASSUMPTION]` and surface them in `assumptions_to_attack`.
   - Never fabricate test passes, file contents, metrics, or schema columns.

## Small-Model & Context Budget Discipline

- Keep L2 instructions concise, imperative, and structured for `1.5B–7B` model adherence.
- Load L3 `references/`, `checklists/`, and `scripts/` strictly on demand when domain triggers apply.
- Prefer deterministic scripts over prose reasoning for execution-plan checks and anomaly injection.
