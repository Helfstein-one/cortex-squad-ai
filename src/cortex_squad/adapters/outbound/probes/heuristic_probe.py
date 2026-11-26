"""Deterministic regex/heuristic probes for steward, finops and chaos critics."""

import re

from cortex_squad.domain.models.verdict import Evidence

_SECRET = re.compile(
    r"(?i)(password|passwd|secret|api[_-]?key|token)\s*[=:]\s*['\"][^'\"]{6,}['\"]|AKIA[0-9A-Z]{16}"
)
_CPF = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b")
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
_CARTESIAN = re.compile(r"\.crossJoin\(|CROSS\s+JOIN", re.I)
_COLLECT = re.compile(r"\.collect\(\)|\.toPandas\(\)")
_SELECT_STAR = re.compile(r"SELECT\s+\*\s+FROM", re.I)


class HeuristicEvidenceProbe:
    """Implements EvidenceProbePort with simple, auditable, deterministic rules."""

    def collect(self, persona: str, code_patches: dict[str, str]) -> list[Evidence]:
        handler = {
            "data-steward": self._steward,
            "finops-tuner": self._finops,
            "chaos-qa-critic": self._chaos,
        }.get(persona)
        return handler(code_patches) if handler else []

    def _steward(self, patches: dict[str, str]) -> list[Evidence]:
        out: list[Evidence] = []
        for path, code in patches.items():
            if m := _SECRET.search(code):
                out.append(
                    Evidence("data-steward", "secret", f"{path}: hardcoded {m.group(0)[:12]}...")
                )
            if _CPF.search(code):
                out.append(Evidence("data-steward", "pii", f"{path}: raw CPF literal"))
            if _EMAIL.search(code):
                out.append(
                    Evidence("data-steward", "pii", f"{path}: raw e-mail literal", hard=False)
                )
        return out

    def _finops(self, patches: dict[str, str]) -> list[Evidence]:
        out: list[Evidence] = []
        for path, code in patches.items():
            if _CARTESIAN.search(code):
                out.append(Evidence("finops-tuner", "cartesian", f"{path}: cross join"))
            if _COLLECT.search(code):
                out.append(
                    Evidence(
                        "finops-tuner", "driver-collect", f"{path}: collect/toPandas", hard=False
                    )
                )
            if _SELECT_STAR.search(code):
                out.append(Evidence("finops-tuner", "select-star", f"{path}: SELECT *", hard=False))
        return out

    def _chaos(self, patches: dict[str, str]) -> list[Evidence]:
        has_tests = any("test" in path.lower() for path in patches)
        if patches and not has_tests:
            return [Evidence("chaos-qa-critic", "no-tests", "no test file in patches", hard=False)]
        return []
