from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from silhouette_core.pipelines import hl7_to_fhir


def test_message_post_and_notify(tmp_path):
    hl7_path = Path('tests/fixtures/hl7/sample_adt_a01.hl7')
    resp = SimpleNamespace(ok=True, status_code=200)
    with patch('silhouette_core.pipelines.hl7_to_fhir.requests.post', return_value=resp) as mock_post:
        hl7_to_fhir.translate(
            input_path=str(hl7_path),
            rules=None,
            map_path='maps/adt_uscore.yaml',
            bundle='transaction',
            out=str(tmp_path),
            server=None,
            token=None,
            validate=False,
            dry_run=False,
            message_mode=True,
            partner=None,
            message_endpoint='http://example.com/msg',
            notify_url='http://example.com/notify',
        )
    urls = [call.args[0] for call in mock_post.call_args_list]
    assert 'http://example.com/msg' in urls
    assert 'http://example.com/notify' in urls
