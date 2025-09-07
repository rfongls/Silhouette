from silhouette_core.interop.mllp import _wrap_hl7


def test_mllp_payload_wrap():
    b = _wrap_hl7("MSH|^~\\&")
    assert b.startswith(b"\x0b") and b.endswith(b"\x1c\x0d")
