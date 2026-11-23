"""CLI interface for cortex-squad-ai using Typer and Rich."""

import asyncio

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cortex_squad.adapters.outbound.llm.litellm_adapter import LiteLLMAdapter
from cortex_squad.adapters.outbound.memory.sqlite_episodic_store import SqliteEpisodicStore
from cortex_squad.adapters.outbound.sandbox.podman_harness_runner import PodmanHarnessRunner
from cortex_squad.adapters.outbound.skills.markdown_skill_loader import MarkdownSkillLoader
from cortex_squad.application.use_cases.run_mission import RunSquadMissionUseCase

app = typer.Typer(
    name="cortex-squad",
    help="Autonomous Multi-Persona Squad based on CoALA Architecture and LangGraph.",
)
console = Console()


@app.command()
def run(
    mission: str = typer.Option(..., "--mission", "-m", help="Mission description or goal."),
    workspace: str = typer.Option(".", "--workspace", "-w", help="Target workspace path."),
    skills_dir: str = typer.Option("skills", "--skills", "-s", help="Path to skills directory."),
    cycles: int = typer.Option(3, "--max-cycles", "-c", help="Max iterative cycles."),
) -> None:
    """Runs a squad mission with full CoALA loops and empirical harness verification."""
    console.print(
        Panel.fit(
            f"[bold cyan]Initiating Cortex Squad Mission[/bold cyan]\n[white]{mission}[/white]",
            border_style="cyan",
        )
    )

    llm = LiteLLMAdapter()
    memory = SqliteEpisodicStore()
    skill_loader = MarkdownSkillLoader(skills_dir)
    sandbox = PodmanHarnessRunner()

    use_case = RunSquadMissionUseCase(
        llm=llm,
        memory_store=memory,
        skill_loader=skill_loader,
        sandbox=sandbox,
    )

    async def _execute() -> None:
        decision = await use_case.execute(
            goal=mission,
            workspace_path=workspace,
            max_cycles=cycles,
        )

        table = Table(title="Squad Quorum Consensus Verdict")
        table.add_column("Persona", style="cyan")
        table.add_column("Decision", style="magenta")
        table.add_column("Rationale", style="white")

        for vote in decision.votes:
            status_style = "green" if vote.decision.value == "approve" else "red"
            table.add_row(
                vote.persona,
                f"[{status_style}]{vote.decision.value.upper()}[/{status_style}]",
                vote.rationale,
            )

        console.print(table)

        if decision.approved:
            console.print(
                Panel(
                    "[bold green]MISSION COMPLETED - QUORUM APPROVED & HARNESS GREEN[/bold green]"
                )
            )
        else:
            veto_info = (
                f" (Vetoing: {decision.vetoing_personas})" if decision.vetoing_personas else ""
            )
            console.print(
                Panel(f"[bold red]MISSION HALTED - VETOED OR HARNESS FAILED{veto_info}[/bold red]")
            )

    asyncio.run(_execute())


@app.command()
def skills(
    skills_dir: str = typer.Option("skills", "--skills", "-s", help="Path to skills directory."),
) -> None:
    """Lists all discovered progressive skills and their triggers."""
    loader = MarkdownSkillLoader(skills_dir)
    discovered = loader.discover_skills()

    table = Table(title="Discovered Cognitive Skills (L1 Progressive Disclosure)")
    table.add_column("Name", style="bold cyan")
    table.add_column("Persona", style="white")
    table.add_column("Role Type", style="yellow")
    table.add_column("Veto Power", style="red")
    table.add_column("Triggers", style="green")

    for sk in discovered:
        table.add_row(
            sk.name,
            sk.persona,
            sk.role_type,
            "YES" if sk.veto_power else "NO",
            ", ".join(sk.triggers),
        )

    console.print(table)


if __name__ == "__main__":
    app()
