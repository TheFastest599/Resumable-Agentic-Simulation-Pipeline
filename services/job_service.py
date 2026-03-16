import logging
import uuid
from typing import Optional

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.redis_client import enqueue_job, remove_job_from_queue, set_pause_flag

logger = logging.getLogger(__name__)
from models.dependency import JobDependency
from models.job import Job
from schemas.job import JobSubmitRequest


async def submit_job(
    db: AsyncSession,
    redis: aioredis.Redis,
    req: JobSubmitRequest,
) -> Job:
    job = Job(
        task_name=req.task_name,
        payload=req.payload,
        priority=req.priority,
        max_retries=req.max_retries,
        status="PENDING",
    )
    db.add(job)
    await db.flush()  # get job.id

    # Store dependency edges
    for dep_id in req.depends_on:
        dep = JobDependency(job_id=job.id, depends_on_job_id=dep_id)
        db.add(dep)

    await db.commit()
    await db.refresh(job)

    # Only enqueue if there are no unmet dependencies
    if not req.depends_on:
        job.status = "QUEUED"
        await db.commit()
        await db.refresh(job)
        await enqueue_job(str(job.id), job.priority)

    return job


async def get_job(db: AsyncSession, job_id: uuid.UUID) -> Optional[Job]:
    result = await db.execute(select(Job).where(Job.id == job_id))
    return result.scalar_one_or_none()


async def cancel_job(
    db: AsyncSession,
    redis: aioredis.Redis,
    job_id: uuid.UUID,
) -> Optional[Job]:
    job = await get_job(db, job_id)
    if job is None:
        return None
    if job.status in ("COMPLETED", "CANCELLED", "FAILED"):
        return job

    await remove_job_from_queue(str(job_id))
    job.status = "CANCELLED"
    await db.commit()
    await db.refresh(job)
    return job


async def pause_job(
    db: AsyncSession,
    redis: aioredis.Redis,
    job_id: uuid.UUID,
) -> Optional[Job]:
    job = await get_job(db, job_id)
    if job is None:
        return None

    if job.status == "QUEUED":
        # Remove from Redis immediately — no worker involved yet
        await remove_job_from_queue(str(job_id))
        job.status = "PAUSED"
        await db.commit()
        await db.refresh(job)
        logger.info("Paused QUEUED job %s", job.id)
    elif job.status == "RUNNING":
        # Signal the worker; it will set status=PAUSED at the next progress checkpoint
        await set_pause_flag(str(job_id))
        logger.info("Pause flag set for RUNNING job %s — worker will pause at next checkpoint", job.id)
    else:
        logger.info("Pause skipped — job %s is in state %s", job.id, job.status)

    return job


async def resume_job(
    db: AsyncSession,
    redis: aioredis.Redis,
    job_id: uuid.UUID,
) -> Optional[Job]:
    job = await get_job(db, job_id)
    if job is None:
        return None
    if job.status not in ("PENDING", "FAILED", "CANCELLED", "PAUSED"):
        logger.info("Resume skipped — job %s is in state %s", job.id, job.status)
        return job

    job.status = "QUEUED"
    job.error = None
    job.retry_count = 0
    await db.commit()
    await db.refresh(job)
    await enqueue_job(str(job.id), job.priority)
    logger.info("Resumed job %s — re-enqueued with priority %d", job.id, job.priority)
    return job


async def list_jobs(
    db: AsyncSession,
    status: Optional[str] = None,
    limit: int = 50,
) -> list[Job]:
    stmt = select(Job).order_by(Job.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(Job.status == status)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_jobs_for_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    limit: int = 20,
) -> list[Job]:
    """Return jobs whose IDs appear in messages of a given conversation."""
    from models.message import Message

    stmt = select(Message).where(Message.conversation_id == conversation_id).order_by(
        Message.created_at.desc()
    ).limit(50)
    result = await db.execute(stmt)
    messages = list(result.scalars().all())

    job_ids: list[uuid.UUID] = []
    seen: set[str] = set()
    for msg in messages:
        for jid in msg.related_job_ids or []:
            if jid not in seen:
                seen.add(jid)
                try:
                    job_ids.append(uuid.UUID(jid))
                except ValueError:
                    pass

    if not job_ids:
        return []

    stmt2 = select(Job).where(Job.id.in_(job_ids)).limit(limit)
    result2 = await db.execute(stmt2)
    return list(result2.scalars().all())
