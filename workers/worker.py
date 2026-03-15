import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta

from core.config import settings
from core.db import AsyncSessionLocal
from core.redis_client import dequeue_job, enqueue_job
from models.job import Job
from tasks.registry import TASK_REGISTRY

logger = logging.getLogger(__name__)

LEASE_DURATION = 60  # seconds
HEARTBEAT_INTERVAL = 10  # seconds
BASE_RETRY_DELAY = 5  # seconds


async def _heartbeat(job_id: uuid.UUID, stop_event: asyncio.Event) -> None:
    """Periodically extend the lease while the job is running."""
    while not stop_event.is_set():
        try:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            if stop_event.is_set():
                break
            async with AsyncSessionLocal() as db:
                job = await db.get(Job, job_id)
                if job and job.status == "RUNNING":
                    job.lease_expiry = datetime.now(timezone.utc) + timedelta(seconds=LEASE_DURATION)
                    await db.commit()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.warning("Heartbeat error for job %s: %s", job_id, e)


async def _execute_job(job: Job) -> dict:
    task_fn = TASK_REGISTRY.get(job.task_name)
    if task_fn is None:
        raise ValueError(f"Unknown task: {job.task_name}")

    loop = asyncio.get_running_loop()
    job_id = job.id

    def sync_progress(value: float) -> None:
        """Called from executor thread — uses its own pooled session to avoid
        concurrent-commit conflicts with the outer process_job session."""
        async def _update():
            try:
                async with AsyncSessionLocal() as progress_db:
                    j = await progress_db.get(Job, job_id)
                    if j:
                        j.progress = round(min(max(value, 0.0), 1.0), 4)
                        await progress_db.commit()
            except Exception:
                pass

        asyncio.run_coroutine_threadsafe(_update(), loop)

    result = await loop.run_in_executor(None, task_fn, job.payload, sync_progress)
    return result


async def process_job(job_id_str: str) -> None:
    async with AsyncSessionLocal() as db:
        job = await db.get(Job, uuid.UUID(job_id_str))
        if job is None:
            logger.warning("Job %s not found in DB — skipping.", job_id_str)
            return

        if job.status != "QUEUED":
            logger.info("Job %s is in state %s — skipping.", job_id_str, job.status)
            return

        # Mark RUNNING and set initial lease
        job.status = "RUNNING"
        job.started_at = datetime.now(timezone.utc)
        job.worker_id = settings.WORKER_ID
        job.lease_expiry = datetime.now(timezone.utc) + timedelta(seconds=LEASE_DURATION)
        await db.commit()

        stop_event = asyncio.Event()
        heartbeat_task = asyncio.create_task(_heartbeat(job.id, stop_event))

        try:
            logger.info("[%s] Running job %s (%s)", settings.WORKER_ID, job_id_str, job.task_name)
            result = await _execute_job(job)

            job.status = "COMPLETED"
            job.result = result
            job.progress = 1.0
            job.finished_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info("[%s] Job %s COMPLETED", settings.WORKER_ID, job_id_str)

            # Unblock DAG dependents
            from services.dag_executor import check_and_unblock
            await check_and_unblock(job.id)

        except asyncio.CancelledError:
            job.status = "CANCELLED"
            await db.commit()
            logger.info("[%s] Job %s CANCELLED", settings.WORKER_ID, job_id_str)
            raise

        except Exception as exc:
            logger.exception("[%s] Job %s FAILED: %s", settings.WORKER_ID, job_id_str, exc)
            job.retry_count += 1
            job.error = str(exc)

            if job.retry_count <= job.max_retries:
                delay = BASE_RETRY_DELAY * (2 ** (job.retry_count - 1))
                logger.info(
                    "[%s] Retrying job %s in %ds (attempt %d/%d)",
                    settings.WORKER_ID, job_id_str, delay, job.retry_count, job.max_retries,
                )
                job.status = "QUEUED"
                await db.commit()
                await asyncio.sleep(delay)
                await enqueue_job(str(job.id), job.priority)
            else:
                job.status = "FAILED"
                job.finished_at = datetime.now(timezone.utc)
                await db.commit()
                logger.info("[%s] Job %s permanently FAILED", settings.WORKER_ID, job_id_str)

        finally:
            stop_event.set()
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass


async def worker_loop() -> None:
    logger.info("[%s] Worker started.", settings.WORKER_ID)
    while True:
        try:
            job_id = await dequeue_job(timeout=2.0)
            if job_id is None:
                continue
            await process_job(job_id)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.exception("Unexpected worker error: %s", e)
            await asyncio.sleep(1)
