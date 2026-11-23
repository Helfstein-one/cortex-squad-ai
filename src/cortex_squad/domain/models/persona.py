"""Domain models for Persona definitions and Deliberations."""

from dataclasses import dataclass, field
from enum import StrEnum


class PersonaRole(StrEnum):
    PRINCIPAL_ARCHITECT = "principal-architect"
    STAFF_DATA_ENGINEER = "staff-data-engineer"
    STAFF_SOFTWARE_ENGINEER = "staff-software-engineer"
    CHAOS_QA_CRITIC = "chaos-qa-critic"
    FINOPS_TUNER = "finops-tuner"
    DATA_STEWARD = "data-steward"


class PersonaRoleType(StrEnum):
    CONCEPTUALIZER = "conceptualizer"
    BUILDER = "builder"
    CRITIC = "critic"
    AUDITOR = "auditor"


@dataclass(frozen=True)
class PersonaSpec:
    name: str
    role: PersonaRole
    role_type: PersonaRoleType
    description: str
    triggers: list[str]
    required_ports: list[str]
    veto_power: bool = False
    max_deliberation_options: int = 3


@dataclass(frozen=True)
class DeliberationOption:
    option_id: str
    title: str
    description: str
    tradeoffs: dict[str, str]  # dimension -> pros/cons evaluation
    score: float = 0.0


@dataclass(frozen=True)
class DeliberationResult:
    persona: str
    options: list[DeliberationOption]
    selected_option_id: str
    selection_justification: str
    files_modified: list[str] = field(default_factory=list)
    code_patches: dict[str, str] = field(default_factory=dict)
    assumptions_to_attack: list[str] = field(default_factory=list)
