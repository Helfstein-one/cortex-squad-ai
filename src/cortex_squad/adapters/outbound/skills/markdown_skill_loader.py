"""Markdown Skill Loader with progressive disclosure (L1 -> L2 -> L3)."""

from pathlib import Path
from typing import Any

import yaml

from cortex_squad.application.ports.skill_port import SkillLoaderPort
from cortex_squad.domain.exceptions import SkillNotFoundError
from cortex_squad.domain.models.skill import LoadedSkill, SkillLevel, SkillMetadata


class MarkdownSkillLoader(SkillLoaderPort):
    """Parses SKILL.md files and loads resources according to progressive disclosure levels."""

    def __init__(self, skills_dir: Path | str):
        self._skills_dir = Path(skills_dir)

    def discover_skills(self) -> list[SkillMetadata]:
        skills: list[SkillMetadata] = []
        if not self._skills_dir.exists():
            return skills

        for skill_file in self._skills_dir.glob("*/SKILL.md"):
            metadata = self._parse_frontmatter(skill_file)
            if metadata:
                skills.append(metadata)
        return skills

    def load_skill(
        self, persona_name: str, level: SkillLevel = SkillLevel.L2_INSTRUCTIONS
    ) -> LoadedSkill:
        skill_dir = self._skills_dir / persona_name
        skill_file = skill_dir / "SKILL.md"

        if not skill_file.exists():
            raise SkillNotFoundError(f"Skill file not found for persona: {persona_name}")

        metadata, body = self._parse_file_parts(skill_file)

        references: dict[str, str] = {}
        checklists: dict[str, str] = {}
        scripts: dict[str, str] = {}

        # L3: Progressive disclosure of heavy assets (references, checklists, scripts)
        if level == SkillLevel.L3_RESOURCES:
            ref_dir = skill_dir / "references"
            if ref_dir.exists():
                for f in ref_dir.glob("*.md"):
                    references[f.name] = f.read_text(encoding="utf-8")

            chk_dir = skill_dir / "checklists"
            if chk_dir.exists():
                for f in chk_dir.glob("*.md"):
                    checklists[f.name] = f.read_text(encoding="utf-8")

            scr_dir = skill_dir / "scripts"
            if scr_dir.exists():
                for f in scr_dir.glob("*.py"):
                    scripts[f.name] = f.read_text(encoding="utf-8")

        return LoadedSkill(
            metadata=metadata,
            level=level,
            body_markdown=body if level >= SkillLevel.L2_INSTRUCTIONS else "",
            references=references,
            checklists=checklists,
            scripts=scripts,
        )

    def _parse_file_parts(self, file_path: Path) -> tuple[SkillMetadata, str]:
        content = file_path.read_text(encoding="utf-8")
        if not content.startswith("---"):
            raise ValueError(f"SKILL.md missing YAML frontmatter: {file_path}")

        parts = content.split("---", 2)
        if len(parts) < 3:
            raise ValueError(f"Malformed YAML frontmatter in: {file_path}")

        raw_yaml = parts[1]
        body = parts[2].strip()
        data: dict[str, Any] = yaml.safe_load(raw_yaml) or {}

        metadata = SkillMetadata(
            name=data.get("name", file_path.parent.name),
            persona=data.get("persona", file_path.parent.name),
            role_type=data.get("role_type", "builder"),
            triggers=data.get("triggers", []),
            required_ports=data.get("required_ports", []),
            veto_power=bool(data.get("veto_power", False)),
            max_deliberation_options=int(data.get("max_deliberation_options", 3)),
            description=body[:150],
        )
        return metadata, body

    def _parse_frontmatter(self, file_path: Path) -> SkillMetadata | None:
        try:
            metadata, _ = self._parse_file_parts(file_path)
            return metadata
        except Exception:
            return None
