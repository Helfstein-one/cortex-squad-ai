"""Use case for driving an end-to-end mission across the squad."""

import uuid
from dataclasses import replace

from cortex_squad.application.ports.evidence_port import EvidenceProbePort
from cortex_squad.application.ports.llm_port import LLMPort
from cortex_squad.application.ports.memory_port import MemoryStorePort
from cortex_squad.application.ports.sandbox_port import SandboxExecutorPort
from cortex_squad.application.ports.skill_port import SkillLoaderPort
from cortex_squad.application.use_cases.collect_quorum_votes import CollectQuorumVotesUseCase
from cortex_squad.application.use_cases.execute_coala_step import ExecuteCoALAStepUseCase
from cortex_squad.application.use_cases.validate_harness import ValidateHarnessUseCase
from cortex_squad.domain.models.cognitive import (
    CoALAMemoryContext,
    EpisodicEntry,
    WorkingMemory,
)
from cortex_squad.domain.models.handoff import HandoffPacket
from cortex_squad.domain.models.persona import (
    PersonaRole,
    PersonaRoleType,
    PersonaSpec,
)
from cortex_squad.domain.models.verdict import (
    SquadDecision,
    VoteDecision,
)
from cortex_squad.domain.services.quorum_policy import QuorumPolicy


class RunSquadMissionUseCase:
    """Coordinates squad through Conception, Construction, Review, and Harness validation."""

    def __init__(
        self,
        llm: LLMPort,
        memory_store: MemoryStorePort,
        skill_loader: SkillLoaderPort,
        sandbox: SandboxExecutorPort,
        evidence_probe: EvidenceProbePort | None = None,
    ):
        self._llm = llm
        self._memory_store = memory_store
        self._skill_loader = skill_loader
        self._sandbox = sandbox
        self._coala_step = ExecuteCoALAStepUseCase(llm, skill_loader)
        self._harness_step = ValidateHarnessUseCase(sandbox)
        self._quorum = CollectQuorumVotesUseCase(llm, skill_loader, evidence_probe)

    async def execute(
        self,
        goal: str,
        workspace_path: str,
        max_cycles: int = 3,
    ) -> SquadDecision:
        mission_id = f"mission-{uuid.uuid4().hex[:8]}"

        # Load episodic history from previous missions
        episodic_history = await self._memory_store.get_episodic_history(mission_id)
        semantic_catalog = await self._memory_store.search_semantic_facts(goal)

        working_mem = WorkingMemory(
            mission_id=mission_id,
            goal=goal,
        )

        memory_ctx = CoALAMemoryContext(
            working=working_mem,
            episodic_history=episodic_history,
            semantic_catalog=semantic_catalog,
        )

        # 0. Phase 0: Spec (Product Manager)
        pm = PersonaSpec(
            name="product-manager",
            role=PersonaRole.PRODUCT_MANAGER,
            role_type=PersonaRoleType.CONCEPTUALIZER,
            description="Product Manager",
            triggers=["prd", "requirements", "acceptance-criteria"],
            required_ports=["ReadOnlyWorkspacePort"],
        )
        pm_result = await self._coala_step.execute(pm, memory_ctx)
        packet = HandoffPacket().with_spec(
            pm_result.selection_justification, pm_result.assumptions_to_attack
        )
        memory_ctx = CoALAMemoryContext(
            working=WorkingMemory(
                mission_id=mission_id,
                goal=goal,
                current_adr=f"SPEC: {pm_result.selection_justification}",
                active_assumptions=pm_result.assumptions_to_attack,
            ),
            episodic_history=episodic_history,
            semantic_catalog=semantic_catalog,
            handoff=packet,
        )

        # 1. Phase 1: Conception (Principal Architect)
        architect = PersonaSpec(
            name="principal-architect",
            role=PersonaRole.PRINCIPAL_ARCHITECT,
            role_type=PersonaRoleType.CONCEPTUALIZER,
            description="Principal Architect",
            triggers=["adr", "architecture", "system-design"],
            required_ports=["ReadOnlyWorkspacePort"],
            veto_power=True,
        )
        arch_result = await self._coala_step.execute(architect, memory_ctx)
        current_adr = arch_result.selection_justification
        packet = packet.with_adr(current_adr, arch_result.assumptions_to_attack)
        harness_logs: list[str] = []

        # 2. Iterative Construction & Empirical Convergence Loop
        for cycle in range(1, max_cycles + 1):
            working_mem = WorkingMemory(
                mission_id=mission_id,
                goal=goal,
                current_adr=current_adr,
                code_diffs=arch_result.code_patches,
                active_assumptions=arch_result.assumptions_to_attack,
                harness_logs=harness_logs,
                iteration_count=cycle,
            )
            memory_ctx = CoALAMemoryContext(
                working=working_mem,
                episodic_history=episodic_history,
                semantic_catalog=semantic_catalog,
                handoff=packet,
            )

            # Phase 2: Construction (Staff Data / Software Engineer)
            engineer = PersonaSpec(
                name="staff-data-engineer",
                role=PersonaRole.STAFF_DATA_ENGINEER,
                role_type=PersonaRoleType.BUILDER,
                description="Staff Data Engineer",
                triggers=["pyspark", "iceberg", "etl", "schema"],
                required_ports=["WorkspaceMutationPort", "SandboxExecutorPort"],
                veto_power=False,
            )
            eng_result = await self._coala_step.execute(engineer, memory_ctx)
            packet = packet.with_build(
                eng_result.files_modified,
                eng_result.code_patches,
                eng_result.assumptions_to_attack,
            )
            memory_ctx = replace(memory_ctx, handoff=packet)

            # Phase 3: Critical Quorum Fan-Out
            votes = await self._quorum.execute(memory_ctx, eng_result.code_patches)

            # Phase 4: Empirical Harness Verification
            harness_report = await self._harness_step.execute(workspace_path)

            decision = QuorumPolicy.evaluate(votes, harness_report)
            harness_logs = [harness_report.raw_logs[:500]]

            if decision.approved:
                return decision

            # Record failure in Episodic Memory to steer next iteration
            failure_sig = (
                f"HarnessFail-Cycle-{cycle}"
                if not harness_report.passed
                else f"VetoBy-{','.join(decision.vetoing_personas)}"
            )
            sm = PersonaSpec(
                name="scrum-master",
                role=PersonaRole.SCRUM_MASTER,
                role_type=PersonaRoleType.FACILITATOR,
                description="Scrum Master",
                triggers=["retro", "blocker", "sprint"],
                required_ports=["ReadOnlyWorkspacePort"],
            )
            remediations = [r for v in votes for r in v.required_remediations]
            remediations += list(harness_report.failure_signatures)
            packet = packet.with_vetoes(
                [
                    f"{v.persona}: {'; '.join(v.evidence or v.blocking_reasons)}"
                    for v in votes
                    if v.decision == VoteDecision.VETO
                ],
                remediations,
            )
            memory_ctx = replace(memory_ctx, handoff=packet)
            retro = await self._coala_step.execute(sm, memory_ctx)
            episodic_entry = EpisodicEntry(
                id=str(uuid.uuid4()),
                mission_id=mission_id,
                failure_signature=failure_sig,
                root_cause=harness_report.raw_logs[:300]
                if not harness_report.passed
                else "Vetoed by critical squad",
                remediation_hint=retro.selection_justification or "Address test failures.",
                persona_culprit="staff-data-engineer",
            )
            await self._memory_store.save_episodic_entry(episodic_entry)
            episodic_history.append(episodic_entry)

        return decision
