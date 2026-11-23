"""Per-persona structural tests (one id per persona)."""

import pytest

from cortex_squad.adapters.outbound.skills.markdown_skill_loader import MarkdownSkillLoader
from cortex_squad.domain.models.skill import SkillLevel

PERSONAS = [
    "principal-architect",
    "staff-data-engineer",
    "staff-software-engineer",
    "chaos-qa-critic",
    "finops-tuner",
    "data-steward",
    "product-manager",
    "scrum-master",
]


@pytest.mark.parametrize("name", PERSONAS)
def test_l1_metadata_is_valid(name: str) -> None:
    skill = MarkdownSkillLoader("skills").load_skill(name, SkillLevel.L1_METADATA)
    md = skill.metadata
    assert md.name == name and md.triggers and md.required_ports
    assert skill.body_markdown == ""


@pytest.mark.parametrize("name", PERSONAS)
def test_l2_body_has_protocol_and_handoff(name: str) -> None:
    body = MarkdownSkillLoader("skills").load_skill(name).body_markdown
    assert "Handoff" in body or "handoff" in body
    assert len(body.split()) < 1500


@pytest.mark.parametrize("name", PERSONAS)
def test_l3_loads_without_error(name: str) -> None:
    skill = MarkdownSkillLoader("skills").load_skill(name, SkillLevel.L3_RESOURCES)
    assert skill.body_markdown
