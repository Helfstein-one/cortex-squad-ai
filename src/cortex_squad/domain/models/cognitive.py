"""Domain models for CoALA Cognitive Architecture."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from cortex_squad.domain.models.handoff import HandoffPacket


class MemoryType(StrEnum):
    WORKING = "working"
    PROCEDURAL = "procedural"
    SEMANTIC = "semantic"
    EPISODIC = "episodic"


@dataclass(frozen=True)
class WorkingMemory:
    mission_id: str
    goal: str
    current_adr: str = ""
    code_diffs: dict[str, str] = field(default_factory=dict)
    active_assumptions: list[str] = field(default_factory=list)
    harness_logs: list[str] = field(default_factory=list)
    iteration_count: int = 0


@dataclass(frozen=True)
class EpisodicEntry:
    id: str
    mission_id: str
    failure_signature: str
    root_cause: str
    remediation_hint: str
    persona_culprit: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SemanticFact:
    key: str
    category: str  # e.g., "schema", "contract", "adr", "business_rule"
    content: str
    source_ref: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CoALATrace:
    persona: str
    phase: str  # "proposal", "evaluation", "selection", "execution"
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class CoALAMemoryContext:
    working: WorkingMemory
    episodic_history: list[EpisodicEntry] = field(default_factory=list)
    semantic_catalog: list[SemanticFact] = field(default_factory=list)
    deliberation_traces: list[CoALATrace] = field(default_factory=list)
    handoff: HandoffPacket = field(default_factory=HandoffPacket)
