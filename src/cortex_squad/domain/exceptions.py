"""Domain exception hierarchy for cortex-squad-ai."""


class CortexSquadError(Exception):
    """Base exception for all domain errors."""


class QuorumVetoError(CortexSquadError):
    """Raised when a persona exercises veto power blocking execution."""


class SkillNotFoundError(CortexSquadError):
    """Raised when requested skill does not exist or cannot be resolved."""


class HarnessExecutionError(CortexSquadError):
    """Raised when the deterministic test harness fails unexpectedly."""


class MemoryStoreError(CortexSquadError):
    """Raised when memory persistence or retrieval encounters errors."""
