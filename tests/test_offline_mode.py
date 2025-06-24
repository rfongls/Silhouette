from silhouette_core.offline_mode import is_offline


def test_is_offline(monkeypatch):
    monkeypatch.delenv("SILHOUETTE_OFFLINE", raising=False)
    assert not is_offline()
    monkeypatch.setenv("SILHOUETTE_OFFLINE", "1")
    assert is_offline()
