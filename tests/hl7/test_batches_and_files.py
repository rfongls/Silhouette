import pytest
from interfaces.hl7.batch import wrap_batch, unwrap_batch
from interfaces.hl7.file_utils import split_messages, normalize_cr


@pytest.mark.hl7
def test_batch_wrap_unwrap_cycle():
    msgs = [
        "MSH|^~\\&|A|B|C|D||ORM^O01|X1|P|2.5.1\rPID|1\r",
        "MSH|^~\\&|A|B|C|D||ORU^R01|X2|P|2.5.1\rPID|1\r",
    ]
    batch = wrap_batch(msgs)
    out = unwrap_batch(batch)
    assert len(out) == 2 and out[0].startswith("MSH|") and out[1].startswith("MSH|")


@pytest.mark.hl7
def test_split_messages_line_endings():
    blob = "MSH|^~\\&|X|Y|Z|Q||VXU^V04|A1|P|2.5.1\nPID|1\nRXA|0|1\n" \
           "MSH|^~\\&|X|Y|Z|Q||ORM^O01|A2|P|2.5.1\rPID|1\rOBR|1\r"
    msgs = split_messages(blob)
    assert len(msgs) == 2
    for m in msgs:
        assert m.endswith("\r")
        assert "\n" not in m
