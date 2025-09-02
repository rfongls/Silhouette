import json
from pathlib import Path

from silhouette_core.pipelines import hl7_to_fhir


def test_partner_profile_override(tmp_path):
    partner_dir = Path('config/partners')
    partner_dir.mkdir(parents=True, exist_ok=True)
    cfg = partner_dir / 'demo.yaml'
    cfg.write_text(
        'profiles:\n  Patient: http://example.org/StructureDefinition/DemoPatient\n',
        encoding='utf-8',
    )
    hl7_path = Path('tests/fixtures/hl7/sample_adt_a01.hl7')
    hl7_to_fhir.translate(
        input_path=str(hl7_path),
        rules=None,
        map_path='maps/adt_uscore.yaml',
        bundle='transaction',
        out=str(tmp_path),
        server=None,
        token=None,
        validate=False,
        dry_run=True,
        message_mode=False,
        partner='demo',
        message_endpoint=None,
        notify_url=None,
    )
    bundle_file = tmp_path / 'fhir/bundles/sample_adt_a01.json'
    data = json.loads(bundle_file.read_text())
    patient_entry = next(
        e for e in data['entry'] if e['resource']['resourceType'] == 'Patient'
    )
    assert patient_entry['resource']['meta']['profile'] == [
        'http://example.org/StructureDefinition/DemoPatient'
    ]
    cfg.unlink()
