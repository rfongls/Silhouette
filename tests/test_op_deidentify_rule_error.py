import asyncio

from engine.contracts import Message
from engine.operators import deidentify as deid_mod
from engine.operators.deidentify import DeidentifyOperator


def test_deidentify_rule_error_does_not_break_run(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(deid_mod, "_apply_single_rule", boom, raising=True)

    msg = Message(
        id="m1",
        raw=b"MSH|^~\\&|A|B|C|D|20250101||ADT^A01|x|P|2.5\rPID|1|||DOE^JOHN\r",
    )
    op = DeidentifyOperator(name="deidentify", actions={"PID-5.1": "remove"}, mode="copy")
    result = asyncio.run(op.process(msg))

    assert result.message is not None
    assert any(issue.code == "deidentify.rule.error" for issue in result.issues)
