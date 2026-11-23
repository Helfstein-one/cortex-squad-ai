"""Use case for triggering empirical verification via Sandbox Executor."""

from cortex_squad.application.ports.sandbox_port import SandboxExecutorPort
from cortex_squad.domain.models.verdict import HarnessReport


class ValidateHarnessUseCase:
    """Invokes the empirical test harness inside isolated container or sandbox."""

    def __init__(self, sandbox_executor: SandboxExecutorPort):
        self._executor = sandbox_executor

    async def execute(
        self,
        workspace_path: str,
        test_commands: list[str] | None = None,
    ) -> HarnessReport:
        return await self._executor.execute_harness(
            workspace_path=workspace_path,
            test_commands=test_commands,
        )
