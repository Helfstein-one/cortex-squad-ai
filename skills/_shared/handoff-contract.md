# Inter-Agent Handoff & Quorum Contract

All personas must exchange state using these schemas so both `cortex-squad-ai` runtime orchestration and standalone/IDE workflows stay lossless and unambiguous.

## 1. Conceptualizer & Builder Output Contract

Aligned 1:1 with `ExecuteCoALAStepUseCase` (`DeliberationResult` JSON):

```json
{
  "options": [
    {
      "option_id": "opt-1",
      "title": "Concise approach title",
      "description": "Implementation/architecture details grounded in verified files",
      "tradeoffs": {"idempotency": "high", "performance": "O(n)", "complexity": "low"},
      "score": 0.9
    }
  ],
  "selected_option_id": "opt-1",
  "selection_justification": "Why opt-1 wins, why others were rejected, [VERIFIED: ...] evidence, and verification_criteria.",
  "files_modified": ["relative/path/to/file.py"],
  "code_patches": {"relative/path/to/file.py": "Full patch or unified diff"},
  "assumptions_to_attack": ["Explicit premise or [ASSUMPTION] for chaos-qa-critic to probe"]
}
```

### Runtime vs. Portable Rules

- Inside `ExecuteCoALAStepUseCase`, emit **valid JSON only** using the exact 6 top-level keys above.
- Embed portable fields inside `selection_justification` (runtime) or as explicit top-level keys (standalone Markdown/IDE handoffs):
  - `evidence`: list of `[VERIFIED: file:line|command]` citations
  - `blocking_ambiguities`: unresolved specification gaps from Phase 0
  - `verification_criteria`: exact commands and expected pass/fail thresholds

## 2. Critic & Auditor Quorum Vote Contract

Aligned 1:1 with `QuorumVote` & `VoteDecision`:

```json
{
  "persona": "chaos-qa-critic | finops-tuner | data-steward",
  "decision": "approve | conditional_approve | veto",
  "rationale": "Evidence-backed summary citing [VERIFIED: file:line|command]",
  "blocking_reasons": ["[CRITICAL] Concrete defect with file/line/metric citation"],
  "required_remediations": ["Concrete, testable action required to clear the block"]
}
```

- Portable extensions (standalone/IDE reviews): `severity` (`CRITICAL | HIGH | MEDIUM | LOW`) and `evidence` (`list[str]`).
- **Actionable Veto Rule**: A `veto` without both non-empty `blocking_reasons` (citing exact file/symbol/metric) and actionable `required_remediations` is invalid.

## 3. RACI & Phase-Scoped Veto Matrix

| Phase / Artifact | `principal-architect` | `staff-data-engineer` | `staff-software-engineer` | `chaos-qa-critic` | `finops-tuner` | `data-steward` |
|---|---|---|---|---|---|---|
| **0. Scope & Ambiguity Gate** | **A / R** | C | C | I | I | C (if PII/regulated) |
| **1. Conception (ADR & Contracts)** | **A / R** (Phase 1 Gate) | C | C | I | C (cost envelope) | C (data class) |
| **2. Construction: Pipelines / SQL / dbt** | I | **R** (No veto) | C (shared Python) | I | I | I |
| **2. Construction: Services / APIs / Python** | I | C (data contracts) | **R** (No veto) | I | I | I |
| **3. Quorum: Resilience & Chaos** | I | I | I | **A / R** (Absolute Veto) | I | I |
| **3. Quorum: Cost & Compute Footprint** | I | I | I | I | **A / R** (Conditional Veto) | I |
| **3. Quorum: LGPD, PII, Secrets & Lineage** | I | I | I | I | I | **A / R** (Absolute Veto) |
| **4. Empirical Harness & Escalation** | **C / Arbitrator** | R (remediate) | R (remediate) | R (evidence) | R (evidence) | R (evidence) |

Legend: **R** = Responsible, **A** = Accountable, **C** = Consulted, **I** = Informed.

### Phase-Scoped Veto Reconciliation

- `principal-architect` (`veto_power: true`) gates **Phase 1 Conception** (rejects uncontracted or tightly coupled designs before construction).
- `QuorumPolicy` governs **Phase 3 Quorum**:
  - **Absolute Veto** (`chaos-qa-critic`, `data-steward`): any `CRITICAL`/`HIGH` correctness, resilience, PII/LGPD, or secrets violation forces `decision: "veto"`.
  - **Conditional Veto** (`finops-tuner`): `decision: "veto"` ONLY for `CRITICAL` or `HIGH` quantified cost/complexity regressions (see `finops-tuner/references/aws-glue-emr-cost.md`). `MEDIUM`/`LOW` findings must use `conditional_approve` or `approve` with advisory notes.
  - **Builders** (`staff-data-engineer`, `staff-software-engineer`): `veto_power: false`.

## 4. Parallel Critic Read-Only Snapshot Isolation

- In Phase 3, `chaos-qa-critic`, `finops-tuner`, and `data-steward` evaluate the **exact same immutable workspace snapshot** and builder `DeliberationResult` in parallel.
- Critics must NOT mutate workspace files or rely on another critic's output to form their independent verdict.

## 5. Disagreement Arbitration & HITL Deadlock Escalation

- **Cycle `< max_cycles` (default `3`)**: If a critic issues a `veto`, builders remediate every item in `required_remediations`. If two critics impose conflicting constraints (e.g., encryption/auditing vs latency/cost), `principal-architect` updates the ADR/interface contract to arbitrate.
- **Deadlock (`cycle >= max_cycles`)**: Do NOT silently ship unapproved changes. Emit a **HITL Escalation Packet**:
  - `mission_goal`, `cycle_count`, `unresolved_vetoes` (persona, reason, remediation), `conflicting_constraints`, `last_harness_failures`, and `recommended_human_decision`.

## 6. Port-to-Environment Tool Mapping

| Logical Port | `cortex-squad-ai` Runtime | Claude Code / Cursor / Codex / Antigravity |
|---|---|---|
| `ReadOnlyWorkspacePort` | Workspace snapshot reader | `Read`, `Grep`, `Glob`, `find`, `view_file` |
| `WorkspaceMutationPort` | Patch / file writer | `Edit`, `Write`, `replace_file_content`, `write_file` |
| `SandboxExecutorPort` | Rootless Podman harness | `Bash`, `run_command` (tests, linters, scripts) |
