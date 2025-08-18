# Auto-generated smoke test
import urllib.request
from skills.http_get_json.v1.wrapper import tool

def test_http_get_json_smoke(monkeypatch):
    class DummyResponse:
        def __init__(self, data):
            self._data = data
        def read(self):
            return self._data
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
    def dummy_urlopen(url, timeout=5.0):
        return DummyResponse(b'{"a":1}')
    monkeypatch.setattr(urllib.request, 'urlopen', dummy_urlopen)
    out = tool('http://example.com')
    assert out == '{"a":1}'
