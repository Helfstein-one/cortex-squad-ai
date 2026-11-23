"""Skill Loader Port interface definition."""

from typing import Protocol

from cortex_squad.domain.models.skill import LoadedSkill, SkillLevel, SkillMetadata


class SkillLoaderPort(Protocol):
    """Port for loading persona skills under progressive disclosure."""

    def discover_skills(self) -> list[SkillMetadata]:
        """Discovers L1 metadata across all available skill manifests."""
        ...

    def load_skill(
        self, persona_name: str, level: SkillLevel = SkillLevel.L2_INSTRUCTIONS
    ) -> LoadedSkill:
        """Loads skill content according to the requested disclosure level."""
        ...
