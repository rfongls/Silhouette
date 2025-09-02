from pathlib import Path

from silhouette_core.pipelines import fhir_to_v2


def test_render_patient_and_observations(tmp_path):
    bundle_path = Path('tests/fixtures/fhir/expected_oru_bundle.json')
    fhir_to_v2.render(str(bundle_path), out=str(tmp_path))
    out_file = tmp_path / (bundle_path.stem + '.hl7')
    text = out_file.read_text()
    assert text.startswith('MSH|^~\\&|SIL|SIL')
    assert 'PID|1|||DOE^JOHN||1980-01-01' in text
    assert 'OBX|1|NM|718-7||13.6' in text
    assert 'OBX|2|NM|4548-4||41.2' in text
