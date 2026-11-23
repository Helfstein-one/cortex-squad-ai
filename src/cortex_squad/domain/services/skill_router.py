"""Domain service for progressive skill routing."""

from cortex_squad.domain.models.skill import SkillMetadata


class SkillRouter:
    """Matches contextual triggers against available skill metadata."""

    @classmethod
    def match_skills(
        cls,
        context_triggers: list[str],
        available_skills: list[SkillMetadata],
    ) -> list[SkillMetadata]:
        normalized_triggers = {t.lower().strip() for t in context_triggers}
        matched: list[SkillMetadata] = []

        for skill in available_skills:
            skill_triggers = {st.lower().strip() for st in skill.triggers}
            if normalized_triggers.intersection(skill_triggers):
                matched.append(skill)

        return matched
