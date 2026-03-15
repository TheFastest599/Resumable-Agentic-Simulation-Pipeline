import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from core.db import AsyncSessionLocal
from core.redis_client import enqueue_job
from models.job import Job

logger = logging.getLogger(__name__)

SCHEDULER_INTERVAL = 30  # seconds


async def recover_zombie_jobs() -> None:
    """Re-queue RUNNING jobs whose lease has expired (worker crashed)."""
    now = datetime.now(timezone.utc)
    async with AsyncSessionLocal() as db:
        stmt = select(Job).where(
            Job.status == "RUNNING",
            Job.lease_expiry < now,
        )
        result = await db.execute(stmt)
        zombies = result.scalars().all()

        for job in zombies:
            logger.warning(
                "Lease expired for job %s (worker %s) — re-queueing.",
                job.id,
                job.worker_id,
            )
            job.status = "QUEUED"
            job.worker_id = None
            job.lease_expiry = None
            await db.commit()
            await enqueue_job(str(job.id), job.priority)


async def run_scheduler() -> None:
    logger.info("Scheduler running (interval=%ds).", SCHEDULER_INTERVAL)
    while True:
        try:
            await asyncio.sleep(SCHEDULER_INTERVAL)
            await recover_zombie_jobs()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.exception("Scheduler error: %s", e)
