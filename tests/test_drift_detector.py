from silhouette_core.drift_detector import detect_drift



def test_detect_drift_simple():
    base = {"positive": 0.5, "negative": 0.5}
    recent = {"positive": 0.1, "negative": 0.9}
    drift = detect_drift(base, recent, 0.3)
    assert drift
    assert "positive" in drift and "negative" in drift
