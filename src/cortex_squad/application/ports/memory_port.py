"""Memory Port interface definition."""

from typing import Protocol

from cortex_squad.domain.models.cognitive import EpisodicEntry, SemanticFact


class MemoryStorePort(Protocol):
    """Port for persisting and retrieving episodic failures and semantic knowledge."""

    async def save_episodic_entry(self, entry: EpisodicEntry) -> None:
        """Stores an episodic failure trace and remediation hint."""
        ...

    async def get_episodic_history(self, mission_id: str, limit: int = 10) -> list[EpisodicEntry]:
        """Retrieves recent failures associated with the current or similar missions."""
        ...

    async def save_semantic_fact(self, fact: SemanticFact) -> None:
        """Indexes an ADR, schema, or contract definition."""
        ...

    async def search_semantic_facts(
        self, query: str, category: str | None = None, limit: int = 5
    ) -> list[SemanticFact]:
        """Retrieves relevant domain facts, schemas, or ADRs."""
        ...
