from __future__ import annotations

import asyncio
import base64
import socket
import socketserver
import threading
from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.endpoints import router as endpoints_router
from api.mllp_send import MLLPSendRequest, send_mllp
from engine.contracts import Message, Result
from engine.net.mllp_server import MLLPServer
from engine.runner import EngineRunner
from engine.sinks.mllp_target import MLLPTargetSink
from engine.spec import dump_pipeline_spec, load_pipeline_spec
from insights.store import get_store, reset_store

PIPELINE_YAML = """
version: 1
name: network-test-pipeline
adapter:
  type: sequence
  config:
    messages:
      - id: "seed"
        text: placeholder
operators: []
sinks:
  - type: memory
"""


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    addr = sock.getsockname()[1]
    sock.close()
    return addr


def test_mllp_inbound_endpoint_enqueues_job(tmp_path, monkeypatch):
    reset_store()
    monkeypatch.setenv("INSIGHTS_DB_URL", f"sqlite:///{tmp_path / 'network.db'}")
    store = get_store()
    store.ensure_schema()
    spec = load_pipeline_spec(PIPELINE_YAML)
    pipeline = store.save_pipeline(
        name="network-test-pipeline",
        yaml=PIPELINE_YAML,
        spec=dump_pipeline_spec(spec),
    )

    app = FastAPI()
    app.include_router(endpoints_router)
    client = TestClient(app)

    port = _free_port()
    create = client.post(
        "/api/engine/endpoints",
        json={
            "kind": "mllp_in",
            "name": "adt-in",
            "pipeline_id": pipeline.id,
            "config": {
                "host": "127.0.0.1",
                "port": port,
                "allow_cidrs": ["127.0.0.1/32"],
            },
        },
    )
    assert create.status_code == 201, create.text
    endpoint_id = create.json()["id"]

    endpoint = store.get_endpoint(endpoint_id)
    assert endpoint is not None
    server = MLLPServer(
        host=str(endpoint.config["host"]),
        port=int(endpoint.config["port"]),
        allow_cidrs=list(endpoint.config.get("allow_cidrs", [])),
        pipeline_id=pipeline.id,
        store=store,
    )

    loop = asyncio.new_event_loop()
    ready = threading.Event()

    def _loop_runner() -> None:
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(server.start())
        except Exception:  # pragma: no cover - defensive
            ready.set()
            raise
        else:
            ready.set()
            loop.run_forever()
        finally:
            loop.close()

    thread = threading.Thread(target=_loop_runner, daemon=True)
    thread.start()
    try:
        assert ready.wait(timeout=5)

        async def _send() -> None:
            reader, writer = await asyncio.open_connection("127.0.0.1", port)
            message = (
                b"MSH|^~\\&|SIL|TEST|LAB|HOSP|202501010101||ADT^A01|MSG0001|P|2.5\r"
                b"PID|1||123||Doe^John\r"
            )
            writer.write(b"\x0b" + message + b"\x1c\x0d")
            await writer.drain()
            ack = await reader.readuntil(b"\x1c\x0d")
            assert ack.startswith(b"\x0bAA")
            writer.close()
            await writer.wait_closed()

        asyncio.run(asyncio.wait_for(_send(), timeout=5))

        jobs = store.list_jobs(status=["queued"], pipeline_id=pipeline.id)
        assert jobs and jobs[0].kind == "ingest"
        payload = jobs[0].payload or {}
        assert payload.get("message_b64")
        assert payload.get("meta", {}).get("peer_ip") == "127.0.0.1"
    finally:
        if loop.is_running():
            async def _shutdown() -> None:
                await server.stop()

            future = asyncio.run_coroutine_threadsafe(_shutdown(), loop)
            future.result(timeout=5)
            loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=5)

    delete = client.delete(f"/api/engine/endpoints/{endpoint_id}")
    assert delete.status_code == 200


def test_engine_runner_executes_ingest_job(tmp_path, monkeypatch):
    reset_store()
    monkeypatch.setenv("INSIGHTS_DB_URL", f"sqlite:///{tmp_path / 'runner.db'}")
    store = get_store()
    store.ensure_schema()
    spec = load_pipeline_spec(PIPELINE_YAML)
    pipeline = store.save_pipeline(
        name="runner-pipeline",
        yaml=PIPELINE_YAML,
        spec=dump_pipeline_spec(spec),
    )

    message = b"MSH|^~\\&|SIL|RUNNER|LAB|HOSP|202501010101||ADT^A08|MSG0002|P|2.5\r"
    payload = {"message_b64": base64.b64encode(message).decode("ascii")}
    store.enqueue_job(pipeline_id=pipeline.id, kind="ingest", payload=payload)

    leased = store.lease_jobs(worker_id="runner", now=datetime.utcnow(), lease_ttl_secs=60, limit=1)
    assert leased
    runner = EngineRunner(store)
    runner.worker_id = "runner"
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    sem = asyncio.Semaphore(1)
    loop.run_until_complete(runner._execute_job(leased[0], sem))
    loop.run_until_complete(asyncio.sleep(0))
    loop.close()
    asyncio.set_event_loop(None)

    job = store.get_job(leased[0].id)
    assert job is not None
    assert job.status == "succeeded"
    assert job.run_id is not None


def test_outbound_sink_and_send_api(tmp_path, monkeypatch):
    reset_store()
    monkeypatch.setenv("INSIGHTS_DB_URL", f"sqlite:///{tmp_path / 'outbound.db'}")
    store = get_store()
    store.ensure_schema()

    port = _free_port()
    received: list[bytes] = []

    class _Handler(socketserver.BaseRequestHandler):
        def handle(self) -> None:  # type: ignore[override]
            data = b""
            while True:
                chunk = self.request.recv(4096)
                if not chunk:
                    break
                data += chunk
                if data.endswith(b"\x1c\x0d"):
                    break
            payload = data[1:-2] if data.startswith(b"\x0b") else data[:-2]
            received.append(payload)
            self.request.sendall(b"\x0bACK\x1c\x0d")

    server = socketserver.ThreadingTCPServer(("127.0.0.1", port), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        store.create_endpoint(
            kind="mllp_out",
            name="adt-out",
            pipeline_id=None,
            config={"host": "127.0.0.1", "port": port},
        )

        sink = MLLPTargetSink(name="mllp_target", target_name="adt-out")
        msg = Message(id="1", raw=b"MSH|^~\\&|SIL|SEND|LAB|HOSP|202501010101||ADT^A31|MSG0003|P|2.5\r")
        result = Result(message=msg, issues=[])
        asyncio.run(asyncio.wait_for(sink.write(result), timeout=5))
        assert received and received[0] == msg.raw

        payload = base64.b64encode(b"MSH|^~\\&|SIL|SEND|LAB|HOSP|202501010202||ADT^A04|MSG0004|P|2.5\r").decode("ascii")
        response = asyncio.run(
            asyncio.wait_for(
                send_mllp(MLLPSendRequest(target_name="adt-out", message_b64=payload)),
                timeout=5,
            )
        )
        assert response.acked is True
        assert len(received) == 2
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
