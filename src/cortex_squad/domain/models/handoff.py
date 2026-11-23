"""Typed handoff packet carried between personas (spec -> ADR -> build -> critics)."""

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class HandoffPacket:
    """Accumulated, immutable baton passed to every persona in the mission."""

    spec: str = ""
    adr: str = ""
    files_modified: tuple[str, ...] = ()
    code_patches: tuple[tuple[str, str], ...] = ()
    assumptions_to_attack: tuple[str, ...] = ()
    open_vetoes: tuple[str, ...] = ()
    required_remediations: tuple[str, ...] = ()

    def with_spec(self, spec: str, assumptions: list[str]) -> "HandoffPacket":
        return replace(
            self,
            spec=spec,
            assumptions_to_attack=_merge(self.assumptions_to_attack, assumptions),
        )

    def with_adr(self, adr: str, assumptions: list[str]) -> "HandoffPacket":
        return replace(
            self,
            adr=adr,
            assumptions_to_attack=_merge(self.assumptions_to_attack, assumptions),
        )

    def with_build(
        self, files: list[str], patches: dict[str, str], assumptions: list[str]
    ) -> "HandoffPacket":
        """Builder output replaces files/patches; assumptions accumulate for the critics."""
        return replace(
            self,
            files_modified=tuple(files),
            code_patches=tuple(patches.items()),
            assumptions_to_attack=_merge(self.assumptions_to_attack, assumptions),
        )

    def with_vetoes(self, vetoes: list[str], remediations: list[str]) -> "HandoffPacket":
        return replace(
            self,
            open_vetoes=tuple(vetoes),
            required_remediations=tuple(remediations),
        )

    def render(self) -> str:
        def block(title: str, items: tuple[str, ...]) -> str:
            body = "\n".join(f"  - {i}" for i in items) or "  (none)"
            return f"{title}:\n{body}"

        return "\n".join(
            [
                f"SPEC (product-manager): {self.spec or '(none)'}",
                f"ADR (principal-architect): {self.adr or '(none)'}",
                block("FILES MODIFIED", self.files_modified),
                block("ASSUMPTIONS TO ATTACK", self.assumptions_to_attack),
                block("OPEN VETOES", self.open_vetoes),
                block("REQUIRED REMEDIATIONS", self.required_remediations),
            ]
        )


def _merge(existing: tuple[str, ...], new: list[str]) -> tuple[str, ...]:
    return existing + tuple(a for a in new if a not in existing)
