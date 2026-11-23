"""Unit tests for SKILL.md structure, frontmatter, and progressive disclosure."""

from cortex_squad.adapters.outbound.skills.markdown_skill_loader import MarkdownSkillLoader
from cortex_squad.domain.models.skill import SkillLevel


def test_markdown_skill_loader_discovers_all_skills() -> None:
    loader = MarkdownSkillLoader("skills")
    discovered = loader.discover_skills()

    names = {s.name for s in discovered}
    expected = {
        "principal-architect",
        "staff-data-engineer",
        "staff-software-engineer",
        "chaos-qa-critic",
        "finops-tuner",
        "data-steward",
    }
    assert expected.issubset(names)


def test_markdown_skill_loader_loads_l2_and_l3() -> None:
    loader = MarkdownSkillLoader("skills")

    # L2: Body instructions
    l2_skill = loader.load_skill("staff-data-engineer", level=SkillLevel.L2_INSTRUCTIONS)
    assert len(l2_skill.body_markdown) > 50
    assert len(l2_skill.references) == 0

    # L3: References and scripts
    l3_skill = loader.load_skill("staff-data-engineer", level=SkillLevel.L3_RESOURCES)
    assert len(l3_skill.body_markdown) > 50
    assert "pyspark-iceberg.md" in l3_skill.references
    assert "explain_plan_check.py" in l3_skill.scripts
