"""Domain services for Quorum validation and consensus."""

from cortex_squad.domain.models.verdict import (
    HarnessReport,
    QuorumVote,
    SquadDecision,
    VoteDecision,
)


class QuorumPolicy:
    """Evaluates squad votes and empirical harness reports to determine mission readiness."""

    # Personas that hold absolute or conditional veto power
    ABSOLUTE_VETO_PERSONAS = {"chaos-qa-critic", "data-steward"}
    CONDITIONAL_VETO_PERSONAS = {"finops-tuner"}

    @classmethod
    def evaluate(
        cls,
        votes: list[QuorumVote],
        harness_report: HarnessReport | None,
    ) -> SquadDecision:
        vetoing_personas: list[str] = []

        for vote in votes:
            if vote.decision == VoteDecision.VETO:
                vetoing_personas.append(vote.persona)

        harness_passed = harness_report.passed if harness_report is not None else False

        # Squad consensus is approved only if:
        # 1. No persona exercised veto.
        # 2. Test harness is 100% green.
        approved = len(vetoing_personas) == 0 and harness_passed

        return SquadDecision(
            approved=approved,
            harness_passed=harness_passed,
            votes=votes,
            harness_report=harness_report,
            vetoing_personas=vetoing_personas,
        )
