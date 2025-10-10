from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.engine import router as engine_router


def test_engine_health_phase2():
    app = FastAPI()
    app.include_router(engine_router)
    client = TestClient(app)

    response = client.get("/api/engine/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("version") == "phase2"
    assert payload.get("feature") == "engine-v2"
