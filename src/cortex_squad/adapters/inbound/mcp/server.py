"""FastMCP Server exposing cortex-squad tools to Antigravity and Agent IDEs."""

from typing import Any

from cortex_squad.adapters.outbound.llm.litellm_adapter import LiteLLMAdapter
from cortex_squad.adapters.outbound.memory.sqlite_episodic_store import SqliteEpisodicStore
from cortex_squad.adapters.outbound.sandbox.podman_harness_runner import PodmanHarnessRunner
from cortex_squad.adapters.outbound.skills.markdown_skill_loader import MarkdownSkillLoader
from cortex_squad.application.use_cases.run_mission import RunSquadMissionUseCase

try:
    from fastmcp import FastMCP

    mcp: Any = FastMCP("cortex-squad-ai")
except ImportError:
    mcp = None


def create_squad_runner() -> RunSquadMissionUseCase:
    return RunSquadMissionUseCase(
        llm=LiteLLMAdapter(),
        memory_store=SqliteEpisodicStore(),
        skill_loader=MarkdownSkillLoader("skills"),
        sandbox=PodmanHarnessRunner(),
    )


if mcp is not None:

    @mcp.tool()  # type: ignore[untyped-decorator]
    async def run_mission(
        goal: str, workspace_path: str = ".", max_cycles: int = 3
    ) -> dict[str, Any]:
        """Runs an autonomous multi-persona engineering squad mission."""
        runner = create_squad_runner()
        decision = await runner.execute(
            goal=goal, workspace_path=workspace_path, max_cycles=max_cycles
        )
        return {
            "approved": decision.approved,
            "harness_passed": decision.harness_passed,
            "vetoing_personas": decision.vetoing_personas,
            "votes": [
                {
                    "persona": v.persona,
                    "decision": v.decision.value,
                    "rationale": v.rationale,
                }
                for v in decision.votes
            ],
        }

    @mcp.tool()  # type: ignore[untyped-decorator]
    def list_squad_skills() -> list[dict[str, Any]]:
        """Lists available persona skills and their activation triggers."""
        loader = MarkdownSkillLoader("skills")
        skills = loader.discover_skills()
        return [
            {
                "name": s.name,
                "persona": s.persona,
                "role_type": s.role_type,
                "triggers": s.triggers,
                "veto_power": s.veto_power,
            }
            for s in skills
        ]


def start_server() -> None:
    if mcp is not None:
        mcp.run()


if __name__ == "__main__":
    start_server()
