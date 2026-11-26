"""Critic quorum: deterministic evidence first, then an LLM vote grounded in it."""

import json
from typing import Any

from cortex_squad.application.ports.evidence_port import EvidenceProbePort
from cortex_squad.application.ports.llm_port import LLMPort
from cortex_squad.application.ports.skill_port import SkillLoaderPort
from cortex_squad.domain.models.cognitive import CoALAMemoryContext
from cortex_squad.domain.models.skill import SkillLevel
from cortex_squad.domain.models.verdict import Evidence, QuorumVote, VoteDecision
from cortex_squad.domain.services.quorum_policy import QuorumPolicy

CRITICS = ("chaos-qa-critic", "finops-tuner", "data-steward")


class NoEvidenceProbe:
    """Default probe: finds nothing."""

    def collect(self, persona: str, code_patches: dict[str, str]) -> list[Evidence]:
        return []


class CollectQuorumVotesUseCase:
    def __init__(
        self,
        llm: LLMPort,
        skill_loader: SkillLoaderPort,
        probe: EvidenceProbePort | None = None,
    ) -> None:
        self._llm = llm
        self._skills = skill_loader
        self._probe: EvidenceProbePort = probe or NoEvidenceProbe()

    async def execute(
        self, ctx: CoALAMemoryContext, code_patches: dict[str, str]
    ) -> list[QuorumVote]:
        return [await self._vote(c, ctx, code_patches) for c in CRITICS]

    async def _vote(
        self, persona: str, ctx: CoALAMemoryContext, patches: dict[str, str]
    ) -> QuorumVote:
        findings = self._probe.collect(persona, patches)
        hard = [f for f in findings if f.hard]
        skill = self._skills.load_skill(persona, SkillLevel.L2_INSTRUCTIONS)
        evidence_text = "\n".join(f"- [{f.kind}] {f.detail}" for f in findings) or "(none)"
        system = (
            f"You are {persona}. {skill.body_markdown}\n\n"
            'Reply with JSON only: {"decision": "approve|conditional_approve|veto", '
            '"rationale": str, "blocking_reasons": [str], "required_remediations": [str], '
            '"evidence": [str]}. A veto MUST cite concrete evidence.'
        )
        user = (
            f"MISSION GOAL: {ctx.working.goal}\n\nHANDOFF PACKET:\n{ctx.handoff.render()}\n\n"
            f"DETERMINISTIC EVIDENCE:\n{evidence_text}\n"
        )
        raw = await self._llm.generate_response(
            persona=persona, system_prompt=system, messages=[{"role": "user", "content": user}]
        )
        parsed = _parse(raw)
        if parsed is None:  # model unusable: fall back to deterministic evidence only
            vote = _from_findings(persona, findings, hard)
        else:
            vote = _from_llm(persona, parsed, findings)
            if hard and vote.decision != VoteDecision.VETO:  # deterministic safety net
                vote = _from_findings(persona, findings, hard)
        return QuorumPolicy.sanitize_vote(vote)


def _parse(raw: str) -> dict[str, Any] | None:
    text = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(text)
    except ValueError:
        return None
    if not isinstance(data, dict) or data.get("decision") not in {m.value for m in VoteDecision}:
        return None
    return data


def _from_llm(persona: str, data: dict[str, Any], findings: list[Evidence]) -> QuorumVote:
    cited = [str(e) for e in data.get("evidence", [])]
    return QuorumVote(
        persona=persona,
        decision=VoteDecision(data["decision"]),
        rationale=str(data.get("rationale", "")),
        blocking_reasons=[str(b) for b in data.get("blocking_reasons", [])],
        required_remediations=[str(r) for r in data.get("required_remediations", [])],
        evidence=cited or [f"[{f.kind}] {f.detail}" for f in findings if f.hard],
    )


def _from_findings(persona: str, findings: list[Evidence], hard: list[Evidence]) -> QuorumVote:
    if hard:
        lines = [f"[{f.kind}] {f.detail}" for f in hard]
        return QuorumVote(
            persona=persona,
            decision=VoteDecision.VETO,
            rationale="Deterministic evidence requires a veto.",
            blocking_reasons=lines,
            required_remediations=[f"Fix: {line}" for line in lines],
            evidence=lines,
        )
    soft = [f"[{f.kind}] {f.detail}" for f in findings]
    return QuorumVote(
        persona=persona,
        decision=VoteDecision.CONDITIONAL_APPROVE if soft else VoteDecision.APPROVE,
        rationale="Soft findings only." if soft else "No findings.",
        required_remediations=soft,
        evidence=soft,
    )
