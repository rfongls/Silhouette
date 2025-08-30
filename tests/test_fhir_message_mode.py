import json
from pathlib import Path

from silhouette_core.pipelines import hl7_to_fhir


def test_translate_message_bundle(tmp_path):
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
        message_mode=True,
        partner=None,
        message_endpoint=None,
        notify_url=None,
    )
    bundle_file = tmp_path / 'fhir/bundles/sample_adt_a01.json'
    data = json.loads(bundle_file.read_text())
    assert data['type'] == 'message'
    header = data['entry'][0]['resource']
    assert header['resourceType'] == 'MessageHeader'
    assert header['eventCoding']['code'] == 'ADT^A01'
    assert len(data['entry']) > 1
