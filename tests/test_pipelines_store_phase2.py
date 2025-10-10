from __future__ import annotations

from engine.spec import dump_pipeline_spec, load_pipeline_spec
from insights.store import InsightsStore, reset_store


def _load_spec(yaml_text: str) -> dict:
    spec = load_pipeline_spec(yaml_text)
    return dump_pipeline_spec(spec)


def test_pipeline_crud_roundtrip(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'pipelines.db'}"
    reset_store()
    store = InsightsStore.from_env(url=db_url)
    store.ensure_schema()

    yaml_text = """
version: 1
name: demo-sequence
adapter:
  type: sequence
  config:
    messages:
      - id: demo-1
        text: hello
operators:
  - type: echo
sinks:
  - type: memory
"""
    spec = _load_spec(yaml_text)
    record = store.save_pipeline(name="demo", description="First", yaml=yaml_text, spec=spec)
    assert record.id is not None
    assert record.name == "demo"
    assert record.description == "First"

    listed = store.list_pipelines()
    assert len(listed) == 1
    assert listed[0].id == record.id

    fetched = store.get_pipeline(record.id)
    assert fetched is not None
    assert fetched.yaml == yaml_text
    assert fetched.spec["name"] == "demo-sequence"

    updated_yaml = yaml_text.replace("demo-sequence", "demo-updated")
    updated_spec = _load_spec(updated_yaml)
    updated = store.save_pipeline(
        pipeline_id=record.id,
        name="demo v2",
        description=None,
        yaml=updated_yaml,
        spec=updated_spec,
    )
    assert updated.id == record.id
    assert updated.name == "demo v2"
    assert updated.description is None

    refreshed = store.get_pipeline(record.id)
    assert refreshed is not None
    assert refreshed.spec["name"] == "demo-updated"

    assert store.delete_pipeline(record.id) is True
    assert store.get_pipeline(record.id) is None
    assert store.delete_pipeline(record.id) is False
