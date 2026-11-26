"""Real critic quorum: evidence-backed vetoes send the mission back to the engineer."""

import json

import pytest

from cortex_squad.adapters.outbound.memory.sqlite_episodic_store import SqliteEpisodicStore
from cortex_squad.adapters.outbound.probes.heuristic_probe import HeuristicEvidenceProbe
from cortex_squad.adapters.outbound.skills.markdown_skill_loader import MarkdownSkillLoader
from cortex_squad.application.use_cases.run_mission import RunSquadMissionUseCase
from cortex_squad.domain.models.verdict import QuorumVote, VoteDecision
from cortex_squad.domain.services.quorum_policy import QuorumPolicy
from tests.e2e_harness.test_squad_convergence import FakeSandboxExecutor

DIRTY = 'API_KEY = "sk-live-abcdef123456"\ndef run(): return 1'
CLEAN = "def run(): return 1"


def _coala(patch: str, justification: str = "ok") -> str:
    return json.dumps(
        {
            "options": [{"option_id": "o1", "title": "t", "description": "d", "tradeoffs": {}}],
            "selected_option_id": "o1",
            "selection_justification": justification,
            "files_modified": ["src/pipeline.py"],
            "code_patches": {"src/pipeline.py": patch},
            "assumptions_to_attack": ["empty input"],
        }
    )


class ReactiveLLM:
    """Engineer fixes the secret only if the remediation reached its prompt."""

    def __init__(self, critic_reply: dict[str, object] | None = None) -> None:
        self.prompts: dict[str, list[str]] = {}
        self.critic_reply = critic_reply

    async def generate_response(
        self,
        persona: str,
        system_prompt: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        **kwargs: object,
    ) -> str:
        prompt = messages[0]["content"]
        self.prompts.setdefault(persona, []).append(prompt)
        if persona == "staff-data-engineer":
            return _coala(CLEAN if "Fix: [secret]" in prompt else DIRTY)
        if persona in {"chaos-qa-critic", "finops-tuner", "data-steward"}:
            reply = self.critic_reply or {"decision": "approve", "rationale": "lgtm"}
            return json.dumps(reply)
        return _coala(CLEAN, "plan")


def _uc(llm: ReactiveLLM) -> RunSquadMissionUseCase:
    return RunSquadMissionUseCase(
        llm=llm,  # type: ignore[arg-type]
        memory_store=SqliteEpisodicStore(":memory:"),
        skill_loader=MarkdownSkillLoader("skills"),
        sandbox=FakeSandboxExecutor(),
        evidence_probe=HeuristicEvidenceProbe(),
    )


@pytest.mark.asyncio
async def test_steward_veto_returns_to_engineer_then_converges() -> None:
    llm = ReactiveLLM()  # critics say "approve"; deterministic evidence must override
    decision = await _uc(llm).execute(goal="g", workspace_path=".", max_cycles=3)
    eng = llm.prompts["staff-data-engineer"]
    assert len(eng) == 2  # vetoed once, fixed once
    assert "data-steward" in eng[1] and "Fix: [secret]" in eng[1]
    assert decision.approved and not decision.vetoing_personas


@pytest.mark.asyncio
async def test_veto_never_clears_when_engineer_cannot_fix() -> None:
    class Stubborn(ReactiveLLM):
        async def generate_response(self, persona: str, *a: object, **k: object) -> str:  # type: ignore[override]
            if persona == "staff-data-engineer":
                return _coala(DIRTY)
            return await super().generate_response(persona, *a, **k)  # type: ignore[arg-type]

    decision = await _uc(Stubborn()).execute(goal="g", workspace_path=".", max_cycles=2)
    assert not decision.approved
    assert decision.vetoing_personas == ["data-steward"]


@pytest.mark.asyncio
async def test_llm_veto_with_evidence_blocks() -> None:
    reply = {"decision": "veto", "rationale": "r", "evidence": ["line 3 skews"]}
    decision = await _uc(ReactiveLLM(reply)).execute(goal="g", workspace_path=".", max_cycles=1)
    assert not decision.approved
    assert {"chaos-qa-critic", "finops-tuner", "data-steward"} <= set(decision.vetoing_personas)


@pytest.mark.asyncio
async def test_llm_veto_without_evidence_is_downgraded() -> None:
    reply = {"decision": "veto", "rationale": "I feel uneasy"}
    llm = ReactiveLLM(reply)
    uc = _uc(llm)
    decision = await uc.execute(goal="g", workspace_path=".", max_cycles=1)
    assert decision.vetoing_personas == ["data-steward"]  # only the evidence-backed one


def test_sanitize_vote_policy() -> None:
    bare = QuorumVote("chaos-qa-critic", VoteDecision.VETO, "x")
    assert QuorumPolicy.sanitize_vote(bare).decision == VoteDecision.CONDITIONAL_APPROVE
    cited = QuorumVote("chaos-qa-critic", VoteDecision.VETO, "x", evidence=["e"])
    assert QuorumPolicy.sanitize_vote(cited).decision == VoteDecision.VETO
