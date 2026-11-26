"""Evidence probe port: deterministic checks that ground critic votes."""

from typing import Protocol

from cortex_squad.domain.models.verdict import Evidence


class EvidenceProbePort(Protocol):
    """Runs deterministic checks for one critic over the builder's code patches."""

    def collect(self, persona: str, code_patches: dict[str, str]) -> list[Evidence]:
        """Returns findings for the given critic persona (empty when clean)."""
        ...
