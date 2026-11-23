"""End-to-end multi-agent convergence test using deterministic test doubles."""

import pytest

from cortex_squad.adapters.outbound.memory.sqlite_episodic_store import SqliteEpisodicStore
from cortex_squad.adapters.outbound.skills.markdown_skill_loader import MarkdownSkillLoader
from cortex_squad.application.ports.llm_port import LLMPort
from cortex_squad.application.ports.sandbox_port import SandboxExecutorPort
from cortex_squad.application.use_cases.run_mission import RunSquadMissionUseCase
from cortex_squad.domain.models.verdict import ExecutionCheckResult, HarnessReport


class FakeLLMAdapter(LLMPort):
    """Deterministic LLM stub producing valid CoALA JSON responses."""

    async def generate_response(
        self,
        persona: str,
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        **kwargs: object,
    ) -> str:
        return """
        {
            "options": [
                {
                    "option_id": "opt-1",
                    "title": "Idempotent Merge",
                    "description": "Deterministic pipeline",
                    "tradeoffs": {"shuffle": "minimal"},
                    "score": 0.98
                }
            ],
            "selected_option_id": "opt-1",
            "selection_justification": "Optimal resource and idempotency",
            "files_modified": ["src/pipeline.py"],
            "code_patches": {"src/pipeline.py": "def process(): return True"},
            "assumptions_to_attack": ["Handles empty dataframe"]
        }
        """


class FakeSandboxExecutor(SandboxExecutorPort):
    """Fake sandbox returning green harness report."""

    async def execute_harness(
        self,
        workspace_path: str,
        test_commands: list[str] | None = None,
    ) -> HarnessReport:
        return HarnessReport(
            passed=True,
            static_analysis_passed=True,
            type_check_passed=True,
            unit_tests_passed=True,
            chaos_tests_passed=True,
            test_results=[ExecutionCheckResult(name="pytest", passed=True, output="1 passed")],
            raw_logs="All checks passed.",
        )


@pytest.mark.asyncio
async def test_squad_convergence_to_green_state() -> None:
    use_case = RunSquadMissionUseCase(
        llm=FakeLLMAdapter(),
        memory_store=SqliteEpisodicStore(":memory:"),
        skill_loader=MarkdownSkillLoader("skills"),
        sandbox=FakeSandboxExecutor(),
    )

    decision = await use_case.execute(
        goal="Build Iceberg idempotency ingestion for sales events",
        workspace_path=".",
        max_cycles=3,
    )

    assert decision.approved is True
    assert decision.harness_passed is True
    assert len(decision.vetoing_personas) == 0
    assert len(decision.votes) == 3
