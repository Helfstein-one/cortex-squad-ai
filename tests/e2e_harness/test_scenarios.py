"""Granular scenario tests: one test id per project question and per phase."""

import pytest

from cortex_squad.adapters.outbound.memory.sqlite_episodic_store import SqliteEpisodicStore
from cortex_squad.adapters.outbound.skills.markdown_skill_loader import MarkdownSkillLoader
from cortex_squad.application.use_cases.run_mission import RunSquadMissionUseCase
from cortex_squad.domain.services.skill_router import SkillRouter
from tests.e2e_harness.scenarios.catalog import SCENARIOS, Scenario
from tests.e2e_harness.test_squad_convergence import (
    FailingSandbox,
    FakeSandboxExecutor,
    RecordingLLM,
)

IDS = [s.id for s in SCENARIOS]


@pytest.mark.parametrize("scenario", SCENARIOS, ids=IDS)
def test_routing_selects_expected_personas(scenario: Scenario) -> None:
    skills = MarkdownSkillLoader("skills").discover_skills()
    matched = {s.name for s in SkillRouter.match_skills(list(scenario.triggers), skills)}
    assert scenario.expected_personas.issubset(matched)


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", SCENARIOS, ids=IDS)
async def test_mission_converges_green(scenario: Scenario) -> None:
    llm = RecordingLLM()
    uc = RunSquadMissionUseCase(
        llm=llm,
        memory_store=SqliteEpisodicStore(":memory:"),
        skill_loader=MarkdownSkillLoader("skills"),
        sandbox=FakeSandboxExecutor(),
    )
    decision = await uc.execute(goal=scenario.question, workspace_path=".", max_cycles=3)
    assert decision.approved
    assert llm.personas[:2] == ["product-manager", "principal-architect"]
    assert "scrum-master" not in llm.personas


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", SCENARIOS, ids=IDS)
async def test_mission_failure_records_episodic_memory(scenario: Scenario) -> None:
    store = SqliteEpisodicStore(":memory:")
    llm = RecordingLLM()
    uc = RunSquadMissionUseCase(
        llm=llm,
        memory_store=store,
        skill_loader=MarkdownSkillLoader("skills"),
        sandbox=FailingSandbox(),
    )
    decision = await uc.execute(goal=scenario.question, workspace_path=".", max_cycles=2)
    assert not decision.approved
    assert llm.personas.count("scrum-master") == 2
    assert len(await store.get_episodic_history("any")) == 2
