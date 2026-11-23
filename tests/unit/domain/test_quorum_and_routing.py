"""Unit tests for Quorum Policy and Skill Router."""

from cortex_squad.domain.models.skill import SkillMetadata
from cortex_squad.domain.models.verdict import HarnessReport, QuorumVote, VoteDecision
from cortex_squad.domain.services.quorum_policy import QuorumPolicy
from cortex_squad.domain.services.skill_router import SkillRouter


def test_quorum_policy_approves_when_all_votes_pass_and_harness_green() -> None:
    votes = [
        QuorumVote(persona="chaos-qa-critic", decision=VoteDecision.APPROVE, rationale="Clean"),
        QuorumVote(persona="data-steward", decision=VoteDecision.APPROVE, rationale="Compliant"),
    ]
    report = HarnessReport(
        passed=True,
        static_analysis_passed=True,
        type_check_passed=True,
        unit_tests_passed=True,
        chaos_tests_passed=True,
    )

    decision = QuorumPolicy.evaluate(votes, report)
    assert decision.approved is True
    assert len(decision.vetoing_personas) == 0


def test_quorum_policy_veto_blocks_even_if_harness_passes() -> None:
    votes = [
        QuorumVote(
            persona="chaos-qa-critic", decision=VoteDecision.VETO, rationale="Edge cases failed"
        ),
        QuorumVote(persona="data-steward", decision=VoteDecision.APPROVE, rationale="Compliant"),
    ]
    report = HarnessReport(
        passed=True,
        static_analysis_passed=True,
        type_check_passed=True,
        unit_tests_passed=True,
        chaos_tests_passed=True,
    )

    decision = QuorumPolicy.evaluate(votes, report)
    assert decision.approved is False
    assert "chaos-qa-critic" in decision.vetoing_personas


def test_quorum_policy_fails_if_harness_fails() -> None:
    votes = [
        QuorumVote(persona="chaos-qa-critic", decision=VoteDecision.APPROVE, rationale="Clean"),
    ]
    report = HarnessReport(
        passed=False,
        static_analysis_passed=False,
        type_check_passed=True,
        unit_tests_passed=True,
        chaos_tests_passed=True,
    )

    decision = QuorumPolicy.evaluate(votes, report)
    assert decision.approved is False
    assert decision.harness_passed is False


def test_skill_router_matches_relevant_triggers() -> None:
    skills = [
        SkillMetadata(
            name="staff-data-engineer",
            persona="Staff Data Engineer",
            role_type="builder",
            triggers=["pyspark", "iceberg", "sql"],
            required_ports=[],
        ),
        SkillMetadata(
            name="data-steward",
            persona="Data Steward",
            role_type="auditor",
            triggers=["pii", "lgpd"],
            required_ports=[],
        ),
    ]

    matched = SkillRouter.match_skills(["iceberg", "delta"], skills)
    assert len(matched) == 1
    assert matched[0].name == "staff-data-engineer"
