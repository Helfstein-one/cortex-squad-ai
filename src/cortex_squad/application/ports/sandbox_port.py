"""Sandbox Executor and Workspace Ports definition."""

from typing import Protocol

from cortex_squad.domain.models.verdict import HarnessReport


class ReadOnlyWorkspacePort(Protocol):
    """ISP: Interface for read-only personas (e.g. Data Steward, Auditors)."""

    def read_file(self, relative_path: str) -> str:
        """Reads content from workspace safely."""
        ...

    def list_files(self, pattern: str = "*") -> list[str]:
        """Lists files in the workspace matching pattern."""
        ...


class WorkspaceMutationPort(ReadOnlyWorkspacePort, Protocol):
    """ISP: Interface for builder personas (e.g. Data Engineer, Software Engineer)."""

    def write_file(self, relative_path: str, content: str) -> None:
        """Writes or updates content in the workspace."""
        ...

    def apply_diff(self, relative_path: str, diff: str) -> None:
        """Applies a patch to an existing file."""
        ...


class SandboxExecutorPort(Protocol):
    """Port for running empirical deterministic test harnesses inside isolated containers."""

    async def execute_harness(
        self,
        workspace_path: str,
        test_commands: list[str] | None = None,
    ) -> HarnessReport:
        """Runs static analysis, mypy, pytest, and chaos probes inside container."""
        ...
