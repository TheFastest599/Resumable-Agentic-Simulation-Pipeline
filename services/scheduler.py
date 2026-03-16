import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from core.db import AsyncSessionLocal
from core.redis_client import enqueue_job
from models.job import Job

logger = logging.getLogger(__name__)

SCHEDULER_INTERVAL = 30  # seconds
AGE_THRESHOLD = 60  # seconds in QUEUED before aging kicks in
AGE_BOOST_PER_INTERVAL = 0.5e12  # ~half a priority level boost per scheduler tick


async def recover_zombie_jobs() -> None:
    """
    1. Re-queue RUNNING jobs whose lease has expired (worker crashed).
    2. Re-queue QUEUED/PENDING jobs that are not in the Redis sorted set
       (enqueue call failed or server restarted).
    """
    from core.redis_client import get_redis
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        # --- Crashed RUNNING jobs ---
        stmt = select(Job).where(
            Job.status == "RUNNING",
            Job.lease_expiry < now,
        )
        result = await db.execute(stmt)
        zombies = result.scalars().all()

        for job in zombies:
            logger.warning(
                "Lease expired for job %s (worker=%s) — re-queuing.",
                job.id, job.worker_id,
            )
            job.status = "QUEUED"
            job.worker_id = None
            job.lease_expiry = None
            await db.commit()
            await enqueue_job(str(job.id), job.priority)

        # --- Orphaned PENDING/QUEUED jobs not in Redis ---
        from models.dependency import JobDependency

        r = get_redis()
        queued_in_redis = set(await r.zrange("job_queue", 0, -1))

        # Jobs that are blocked by an unmet dependency (dep not yet COMPLETED)
        has_unmet_dep = (
            select(JobDependency.job_id)
            .join(Job, Job.id == JobDependency.depends_on_job_id)
            .where(Job.status != "COMPLETED")
        )

        stmt2 = select(Job).where(
            Job.status.in_(["PENDING", "QUEUED"]),
            Job.id.not_in(has_unmet_dep),
        )
        result2 = await db.execute(stmt2)
        orphans = result2.scalars().all()

        for job in orphans:
            if str(job.id) not in queued_in_redis:
                logger.warning(
                    "Orphaned %s job %s not in Redis queue — re-queuing.",
                    job.status, job.id,
                )
                job.status = "QUEUED"
                await db.commit()
                await enqueue_job(str(job.id), job.priority)

        # --- Anti-starvation: age boost for long-waiting QUEUED jobs ---
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=AGE_THRESHOLD)
        stmt3 = select(Job).where(
            Job.status == "QUEUED",
            Job.created_at < cutoff,
        )
        result3 = await db.execute(stmt3)
        aging_jobs = result3.scalars().all()

        for job in aging_jobs:
            await r.zincrby("job_queue", AGE_BOOST_PER_INTERVAL, str(job.id))
            logger.debug(
                "Age boost applied to job %s (priority=%d, waiting>%ds)",
                job.id, job.priority, AGE_THRESHOLD,
            )


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
