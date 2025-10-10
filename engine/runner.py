from __future__ import annotations

import asyncio
import logging
import os
import socket
from datetime import datetime

from engine.runtime import EngineRuntime
from engine.spec import load_pipeline_spec
from insights.store import InsightsStore, JobNotFoundError, JobRecord

logger = logging.getLogger(__name__)

DEFAULT_CONCURRENCY = int(os.getenv("ENGINE_RUNNER_CONCURRENCY", "2"))
LEASE_TTL_SECS = int(os.getenv("ENGINE_RUNNER_LEASE_TTL_SECS", "60"))
POLL_INTERVAL_SECS = float(os.getenv("ENGINE_RUNNER_POLL_INTERVAL_SECS", "0.5"))


def _backoff_secs(attempts: int) -> int:
    base = 2 ** max(0, attempts)
    jitter = attempts % 3
    return min(300, base + jitter or 1)


class EngineRunner:
    """Background worker that leases and executes Engine jobs."""

    def __init__(self, store: InsightsStore, concurrency: int = DEFAULT_CONCURRENCY) -> None:
        self.store = store
        self.concurrency = max(1, concurrency)
        self.worker_id = f"{socket.gethostname()}:{os.getpid()}"
        self._stopped = asyncio.Event()

    async def run_forever(self) -> None:
        """Continuously lease jobs and execute them until stopped."""

        sem = asyncio.Semaphore(self.concurrency)
        tasks: set[asyncio.Task[None]] = set()

        try:
            while not self._stopped.is_set():
                now = datetime.utcnow()
                leased = self.store.lease_jobs(
                    worker_id=self.worker_id,
                    now=now,
                    lease_ttl_secs=LEASE_TTL_SECS,
                    limit=self.concurrency,
                )
                if not leased:
                    await asyncio.sleep(POLL_INTERVAL_SECS)
                    continue

                for job in leased:
                    await sem.acquire()
                    task = asyncio.create_task(self._execute_job(job, sem))
                    tasks.add(task)
                    task.add_done_callback(tasks.discard)
        finally:
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    async def stop(self) -> None:
        self._stopped.set()

    async def _execute_job(self, job: JobRecord, sem: asyncio.Semaphore) -> None:
        started: JobRecord | None = None
        try:
            started = self.store.start_job(job.id, self.worker_id, now=datetime.utcnow())
            if started is None:
                logger.info("job.skip", extra={"job_id": job.id, "reason": "not-leased"})
                return

            logger.info(
                "job.start",
                extra={
                    "job_id": started.id,
                    "pipeline_id": started.pipeline_id,
                    "kind": started.kind,
                    "attempts": started.attempts,
                    "priority": started.priority,
                    "scheduled_at": started.scheduled_at.isoformat(),
                },
            )

            pipeline = self.store.get_pipeline(started.pipeline_id)
            if pipeline is None:
                raise JobNotFoundError(f"pipeline {started.pipeline_id} not found")

            spec = load_pipeline_spec(pipeline.yaml)
            job_payload = started.payload or {}
            max_messages = job_payload.get("max_messages")
            persist = job_payload.get("persist", True)

            runtime = EngineRuntime(spec)
            results = await runtime.run(max_messages=max_messages)

            run_id = None
            if persist:
                run_id = self.store.persist_run_results(
                    pipeline_name=pipeline.name,
                    results=results,
                )

            self.store.complete_job(started.id, run_id)
            logger.info(
                "job.success",
                extra={
                    "job_id": started.id,
                    "run_id": run_id,
                    "processed": len(results),
                },
            )
        except JobNotFoundError as exc:
            logger.error(
                "job.error",
                extra={
                    "job_id": job.id,
                    "status": getattr(started, "status", getattr(job, "status", None)),
                    "error": str(exc),
                },
            )
            self.store.fail_job_and_maybe_retry(
                job_id=job.id,
                error=str(exc),
                now=datetime.utcnow(),
                backoff_secs=_backoff_secs(job.attempts),
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception(
                "job.error",
                extra={
                    "job_id": job.id,
                    "status": getattr(started, "status", getattr(job, "status", None)),
                },
            )
            self.store.fail_job_and_maybe_retry(
                job_id=job.id,
                error=str(exc),
                now=datetime.utcnow(),
                backoff_secs=_backoff_secs(job.attempts),
            )
        finally:
            sem.release()


def main() -> None:
    store = InsightsStore.from_env()
    runner = EngineRunner(store=store, concurrency=DEFAULT_CONCURRENCY)
    asyncio.run(runner.run_forever())


if __name__ == "__main__":  # pragma: no cover - manual execution entrypoint
    main()
