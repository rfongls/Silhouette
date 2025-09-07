import api.interop as interop


def test_trigger_descriptions_load_or_skip():
    csv_path = interop.TRIGGER_CSV_PATH
    if not csv_path.exists():
        assert True
        return
    mapping = interop._load_trigger_descriptions()
    assert isinstance(mapping, dict)
    assert len(mapping) >= 1
    code = "ADT_A01" if "ADT_A01" in mapping else next(iter(mapping.keys()))
    desc = interop._describe_trigger(code)
    assert isinstance(desc, str)
    assert code in mapping
