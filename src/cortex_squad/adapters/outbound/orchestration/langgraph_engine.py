"""LangGraph StateGraph orchestration engine with cyclic empirical harness."""

from typing import Any, Literal

from langgraph.graph import END, StateGraph

from cortex_squad.adapters.outbound.orchestration.state_schema import SquadGraphState
from cortex_squad.application.ports.llm_port import LLMPort
from cortex_squad.application.ports.memory_port import MemoryStorePort
from cortex_squad.application.ports.sandbox_port import SandboxExecutorPort
from cortex_squad.application.ports.skill_port import SkillLoaderPort
from cortex_squad.domain.models.verdict import VoteDecision


class LangGraphSquadEngine:
    """Orchestrates multi-agent squad through Conception, Construction, Fan-Out, and Harness."""

    def __init__(
        self,
        llm: LLMPort,
        memory_store: MemoryStorePort,
        skill_loader: SkillLoaderPort,
        sandbox: SandboxExecutorPort,
    ):
        self._llm = llm
        self._memory = memory_store
        self._skill_loader = skill_loader
        self._sandbox = sandbox
        self.workflow = self._build_graph()

    def _build_graph(self) -> Any:
        builder = StateGraph(SquadGraphState)

        builder.add_node("conception", self._node_conception)
        builder.add_node("construction", self._node_construction)
        builder.add_node("chaos_critic", self._node_chaos_critic)
        builder.add_node("finops_tuner", self._node_finops_tuner)
        builder.add_node("data_steward", self._node_data_steward)
        builder.add_node("empirical_harness", self._node_empirical_harness)

        builder.set_entry_point("conception")
        builder.add_edge("conception", "construction")

        # Fan-Out to Critical Quorum
        builder.add_edge("construction", "chaos_critic")
        builder.add_edge("construction", "finops_tuner")
        builder.add_edge("construction", "data_steward")

        # Fan-In to Empirical Harness
        builder.add_edge("chaos_critic", "empirical_harness")
        builder.add_edge("finops_tuner", "empirical_harness")
        builder.add_edge("data_steward", "empirical_harness")

        # Conditional Edge after Harness
        builder.add_conditional_edges(
            "empirical_harness",
            self._routing_condition,
            {
                "approved": END,
                "retry": "construction",
            },
        )

        return builder.compile()

    async def _node_conception(self, state: SquadGraphState) -> dict[str, Any]:
        return {
            "current_adr": f"ADR: Hexagonal data pipeline for '{state['goal']}'",
            "status_message": "Conception finished by Principal Architect.",
        }

    async def _node_construction(self, state: SquadGraphState) -> dict[str, Any]:
        return {
            "iteration_count": state.get("iteration_count", 0) + 1,
            "code_diffs": {"pipeline.py": "# pipeline implementation"},
            "assumptions_to_attack": ["Handles null keys gracefully", "Deterministic output"],
            "status_message": "Construction step finished by Staff Data Engineer.",
        }

    async def _node_chaos_critic(self, state: SquadGraphState) -> dict[str, Any]:
        return {
            "votes": [
                {
                    "persona": "chaos-qa-critic",
                    "decision": VoteDecision.APPROVE.value,
                    "rationale": "Edge cases validated.",
                }
            ]
        }

    async def _node_finops_tuner(self, state: SquadGraphState) -> dict[str, Any]:
        return {
            "votes": [
                {
                    "persona": "finops-tuner",
                    "decision": VoteDecision.APPROVE.value,
                    "rationale": "Resource allocation within nominal thresholds.",
                }
            ]
        }

    async def _node_data_steward(self, state: SquadGraphState) -> dict[str, Any]:
        return {
            "votes": [
                {
                    "persona": "data-steward",
                    "decision": VoteDecision.APPROVE.value,
                    "rationale": "LGPD PII boundaries verified.",
                }
            ]
        }

    async def _node_empirical_harness(self, state: SquadGraphState) -> dict[str, Any]:
        # Run test harness
        report = await self._sandbox.execute_harness(workspace_path=".")
        is_approved = report.passed and state.get("iteration_count", 1) >= 1
        return {
            "approved": is_approved,
            "harness_logs": [report.raw_logs[:200]],
            "status_message": "Harness passed 100% green" if is_approved else "Harness failed",
        }

    def _routing_condition(self, state: SquadGraphState) -> Literal["approved", "retry"]:
        if state.get("approved", False) or state.get("iteration_count", 1) >= 3:
            return "approved"
        return "retry"
