from cortex_squad.domain.models.handoff import HandoffPacket


def test_packet_accumulates_and_dedups_assumptions() -> None:
    p = HandoffPacket().with_spec("s", ["a"]).with_adr("adr", ["a", "b"])
    assert p.assumptions_to_attack == ("a", "b")
    assert p.spec == "s" and p.adr == "adr"


def test_packet_is_immutable_and_renders() -> None:
    p = HandoffPacket()
    q = p.with_build(["f.py"], {"f.py": "x"}, ["z"]).with_vetoes(["chaos-qa-critic"], ["fix"])
    assert p.files_modified == ()
    text = q.render()
    assert "f.py" in text and "chaos-qa-critic" in text and "fix" in text
