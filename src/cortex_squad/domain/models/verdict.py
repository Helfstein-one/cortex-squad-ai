"""Domain models for Verdicts, Tests, and Quorum Decisions."""

from dataclasses import dataclass, field
from enum import StrEnum


class VoteDecision(StrEnum):
    APPROVE = "approve"
    VETO = "veto"
    CONDITIONAL_APPROVE = "conditional_approve"


@dataclass(frozen=True)
class QuorumVote:
    persona: str
    decision: VoteDecision
    rationale: str
    blocking_reasons: list[str] = field(default_factory=list)
    required_remediations: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExecutionCheckResult:
    name: str
    passed: bool
    output: str = ""
    duration_seconds: float = 0.0


@dataclass(frozen=True)
class HarnessReport:
    passed: bool
    static_analysis_passed: bool
    type_check_passed: bool
    unit_tests_passed: bool
    chaos_tests_passed: bool
    test_results: list[ExecutionCheckResult] = field(default_factory=list)
    raw_logs: str = ""
    failure_signatures: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SquadDecision:
    approved: bool
    harness_passed: bool
    votes: list[QuorumVote]
    harness_report: HarnessReport | None = None
    vetoing_personas: list[str] = field(default_factory=list)
