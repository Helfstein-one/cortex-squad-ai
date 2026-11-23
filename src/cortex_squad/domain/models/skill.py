"""Domain models for Progressive Skills."""

from dataclasses import dataclass, field
from enum import Enum


class SkillLevel(int, Enum):
    L1_METADATA = 1
    L2_INSTRUCTIONS = 2
    L3_RESOURCES = 3


@dataclass(frozen=True)
class SkillMetadata:
    name: str
    persona: str
    role_type: str
    triggers: list[str]
    required_ports: list[str]
    veto_power: bool = False
    max_deliberation_options: int = 3
    description: str = ""


@dataclass(frozen=True)
class LoadedSkill:
    metadata: SkillMetadata
    level: SkillLevel
    body_markdown: str = ""
    references: dict[str, str] = field(default_factory=dict)
    checklists: dict[str, str] = field(default_factory=dict)
    scripts: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SkillActivationRule:
    domain_tags: list[str]
    required_confidence: float = 0.7
