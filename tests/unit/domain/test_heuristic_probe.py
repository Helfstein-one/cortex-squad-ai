import pytest

from cortex_squad.adapters.outbound.probes.heuristic_probe import HeuristicEvidenceProbe

P = HeuristicEvidenceProbe()


@pytest.mark.parametrize(
    ("persona", "code", "kind", "hard"),
    [
        ("data-steward", 'password = "hunter2hunter2"', "secret", True),
        ("data-steward", "cpf = '123.456.789-09'", "pii", True),
        ("data-steward", "mail = 'a@b.com'", "pii", False),
        ("finops-tuner", "df.crossJoin(other)", "cartesian", True),
        ("finops-tuner", "df.toPandas()", "driver-collect", False),
        ("finops-tuner", "SELECT * FROM t", "select-star", False),
    ],
)
def test_probe_detects(persona: str, code: str, kind: str, hard: bool) -> None:
    found = P.collect(persona, {"a.py": code})
    assert [(e.kind, e.hard) for e in found] == [(kind, hard)]


def test_probe_clean_and_chaos_rules() -> None:
    assert P.collect("data-steward", {"a.py": "x = 1"}) == []
    assert P.collect("chaos-qa-critic", {"a.py": "x"})[0].kind == "no-tests"
    assert P.collect("chaos-qa-critic", {"a.py": "x", "test_a.py": "y"}) == []
