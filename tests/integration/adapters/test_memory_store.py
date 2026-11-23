"""Integration tests for SQLite Episodic Store."""

import pytest

from cortex_squad.adapters.outbound.memory.sqlite_episodic_store import SqliteEpisodicStore
from cortex_squad.domain.models.cognitive import EpisodicEntry, SemanticFact


@pytest.mark.asyncio
async def test_sqlite_episodic_store_save_and_retrieve() -> None:
    store = SqliteEpisodicStore(":memory:")

    entry = EpisodicEntry(
        id="fail-1",
        mission_id="mission-123",
        failure_signature="AnalysisException: Column not found",
        root_cause="Schema mismatch in bronze layer",
        remediation_hint="Cast column to string",
        persona_culprit="staff-data-engineer",
    )

    await store.save_episodic_entry(entry)
    history = await store.get_episodic_history("mission-123")

    assert len(history) == 1
    assert history[0].failure_signature == "AnalysisException: Column not found"
    assert history[0].persona_culprit == "staff-data-engineer"


@pytest.mark.asyncio
async def test_sqlite_semantic_store_index_and_search() -> None:
    store = SqliteEpisodicStore(":memory:")

    fact = SemanticFact(
        key="adr-001",
        category="adr",
        content="We use Apache Iceberg with hidden partitioning on event_date.",
        source_ref="skills/principal-architect/templates/adr-template.md",
    )

    await store.save_semantic_fact(fact)
    results = await store.search_semantic_facts("Iceberg")

    assert len(results) == 1
    assert results[0].key == "adr-001"
