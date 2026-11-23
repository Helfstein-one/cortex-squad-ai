"""Deterministic Podman Sandbox Harness Runner."""

import asyncio
import os
import shutil

from cortex_squad.application.ports.sandbox_port import SandboxExecutorPort
from cortex_squad.domain.models.verdict import ExecutionCheckResult, HarnessReport


class PodmanHarnessRunner(SandboxExecutorPort):
    """Executes deterministic test harnesses inside Podman or directly in fallback local sandbox."""

    def __init__(
        self,
        image_name: str = "cortex-squad-harness:latest",
        use_podman_if_available: bool = True,
    ):
        self._image_name = image_name
        self._use_podman = use_podman_if_available and (shutil.which("podman") is not None)

    async def execute_harness(
        self,
        workspace_path: str,
        test_commands: list[str] | None = None,
    ) -> HarnessReport:
        commands = test_commands or [
            "ruff check .",
            "mypy --strict src",
            "pytest -v tests/unit",
        ]

        test_results: list[ExecutionCheckResult] = []
        failure_signatures: list[str] = []
        accumulated_logs: list[str] = []

        all_passed = True
        static_passed = True
        mypy_passed = True
        unit_passed = True
        chaos_passed = True

        for cmd in commands:
            code, stdout, stderr = await self._run_command(cmd, workspace_path)
            passed = code == 0
            accumulated_logs.append(f"$ {cmd}\n{stdout}\n{stderr}")

            test_results.append(
                ExecutionCheckResult(
                    name=cmd,
                    passed=passed,
                    output=stdout + "\n" + stderr,
                )
            )

            if not passed:
                all_passed = False
                failure_signatures.append(f"CommandFailed: {cmd}")
                if "ruff" in cmd:
                    static_passed = False
                elif "mypy" in cmd:
                    mypy_passed = False
                elif "chaos" in cmd or "probe" in cmd:
                    chaos_passed = False
                else:
                    unit_passed = False

        return HarnessReport(
            passed=all_passed,
            static_analysis_passed=static_passed,
            type_check_passed=mypy_passed,
            unit_tests_passed=unit_passed,
            chaos_tests_passed=chaos_passed,
            test_results=test_results,
            raw_logs="\n".join(accumulated_logs),
            failure_signatures=failure_signatures,
        )

    async def _run_command(self, cmd: str, cwd: str) -> tuple[int, str, str]:
        if self._use_podman:
            # Wrap command in rootless podman run with workspace mounted read-only or scoped
            full_cmd = (
                f"podman run --rm -v {os.path.abspath(cwd)}:/workspace:rw "
                f"-w /workspace {self._image_name} {cmd}"
            )
            # If image doesn't exist locally, fallback gracefully to local execution
            try:
                proc = await asyncio.create_subprocess_shell(
                    full_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout_b, stderr_b = await proc.communicate()
                if proc.returncode != 125:  # 125 is docker/podman image error
                    return (
                        proc.returncode or 0,
                        stdout_b.decode(errors="replace"),
                        stderr_b.decode(errors="replace"),
                    )
            except Exception:
                pass

        # Local execution fallback
        proc = await asyncio.create_subprocess_shell(
            cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_b, stderr_b = await proc.communicate()
        return (
            proc.returncode or 0,
            stdout_b.decode(errors="replace"),
            stderr_b.decode(errors="replace"),
        )
