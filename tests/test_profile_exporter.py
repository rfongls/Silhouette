from silhouette_core.profile_exporter import collect_profile, export_profile


def test_collect_profile(tmp_path):
    persona = tmp_path / "persona.dsl"
    persona.write_text("rules")
    memory = tmp_path / "memory.jsonl"
    memory.write_text('{"content": "hi"}\n')
    modules = tmp_path / "modules"
    modules.mkdir()
    (modules / "m.json").write_text('{"name": "m", "version": "1"}')
    manifest = tmp_path / "PROJECT_MANIFEST.json"
    manifest.write_text('{"version": "0"}')

    profile = collect_profile(persona, memory, modules, manifest)
    assert profile["memory"]["entries"] == 1
    assert profile["modules"][0]["name"] == "m"


def test_export_profile(tmp_path):
    out = tmp_path / "p.json"
    result = export_profile(out, as_zip=False)
    assert result.exists()
