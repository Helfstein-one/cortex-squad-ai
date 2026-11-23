"""Use Case for executing CoALA cognitive loops: Proposal -> Eval -> Select -> Exec."""

import json
from typing import Any

from cortex_squad.application.ports.llm_port import LLMPort
from cortex_squad.application.ports.skill_port import SkillLoaderPort
from cortex_squad.domain.models.cognitive import CoALAMemoryContext
from cortex_squad.domain.models.persona import DeliberationOption, DeliberationResult, PersonaSpec
from cortex_squad.domain.models.skill import SkillLevel


class ExecuteCoALAStepUseCase:
    """Orchestrates an agent's internal deliberation cycle according to the CoALA architecture."""

    def __init__(self, llm_adapter: LLMPort, skill_loader: SkillLoaderPort):
        self._llm = llm_adapter
        self._skill_loader = skill_loader

    async def execute(
        self,
        persona: PersonaSpec,
        memory_ctx: CoALAMemoryContext,
    ) -> DeliberationResult:
        # 1. Retrieval & Procedural progressive disclosure (L2 & L3 if needed)
        loaded_skill = self._skill_loader.load_skill(
            persona_name=persona.name,
            level=SkillLevel.L2_INSTRUCTIONS,
        )

        # Build context prompt with CoALA layers: Working, Semantic, and Episodic failures
        failures = [
            f"- [FAIL] {e.failure_signature} | Cause: {e.root_cause} | Hint: {e.remediation_hint}"
            for e in memory_ctx.episodic_history
        ]
        episodic_summary = "\n".join(failures) or "None. Clean record."

        max_opts = persona.max_deliberation_options
        system_prompt = f"""
You are {persona.name} ({persona.role_type.value}).
{loaded_skill.body_markdown}

COALA DELIBERATION PROTOCOL:
1. Retrieval: You must respect past episodic failures and adhere strictly to semantic contracts.
2. Proposal: Propose between 2 and {max_opts} distinct architectural/code solutions.
3. Evaluation: Compare them across trade-offs (Idempotency, Performance, Simplicity, Testability).
4. Selection: Select the superior option with rigorous justification.
5. Execution: Generate the code diff / modifications and list assumptions to attack.

RESPONSE FORMAT (Valid JSON only):
{{
  "options": [
    {{
      "option_id": "opt-1",
      "title": "Title of approach",
      "description": "Details",
      "tradeoffs": {{"performance": "...", "complexity": "..."}},
      "score": 0.9
    }}
  ],
  "selected_option_id": "opt-1",
  "selection_justification": "Why this option is optimal",
  "files_modified": ["path/to/file.py"],
  "code_patches": {{"path/to/file.py": "# code here"}},
  "assumptions_to_attack": ["Assumption 1", "Assumption 2"]
}}
"""

        log_preview = (
            "".join(memory_ctx.working.harness_logs[-5:])
            if memory_ctx.working.harness_logs
            else "No prior execution."
        )

        user_content = f"""
MISSION GOAL: {memory_ctx.working.goal}
CURRENT ARCHITECTURAL DECISION / CONTEXT:
{memory_ctx.working.current_adr}

EPISODIC MEMORY (PAST FAILURES TO AVOID):
{episodic_summary}

HARNESS LOGS (FROM PRIOR ITERATION):
{log_preview}
"""

        messages = [{"role": "user", "content": user_content}]
        raw_response = await self._llm.generate_response(
            persona=persona.name,
            system_prompt=system_prompt,
            messages=messages,
        )

        parsed: dict[str, Any] = self._parse_json(raw_response)

        options = [
            DeliberationOption(
                option_id=opt["option_id"],
                title=opt.get("title", ""),
                description=opt.get("description", ""),
                tradeoffs=opt.get("tradeoffs", {}),
                score=float(opt.get("score", 0.0)),
            )
            for opt in parsed.get("options", [])
        ]

        result = DeliberationResult(
            persona=persona.name,
            options=options,
            selected_option_id=parsed.get("selected_option_id", ""),
            selection_justification=parsed.get("selection_justification", ""),
            files_modified=parsed.get("files_modified", []),
            code_patches=parsed.get("code_patches", {}),
            assumptions_to_attack=parsed.get("assumptions_to_attack", []),
        )

        return result

    def _parse_json(self, raw_str: str) -> dict[str, Any]:
        cleaned = raw_str.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned.removeprefix("```json").removesuffix("```").strip()
        elif cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```").removesuffix("```").strip()
        try:
            return json.loads(cleaned)  # type: ignore[no-any-return]
        except Exception:
            return {
                "options": [
                    {
                        "option_id": "fallback-1",
                        "title": "Default synthesis",
                        "description": cleaned[:200],
                        "tradeoffs": {"risk": "low"},
                        "score": 0.8,
                    }
                ],
                "selected_option_id": "fallback-1",
                "selection_justification": "Direct synthesized output",
                "files_modified": [],
                "code_patches": {},
                "assumptions_to_attack": [],
            }
