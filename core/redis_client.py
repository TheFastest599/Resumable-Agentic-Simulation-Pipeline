import logging
import time

import redis.asyncio as aioredis

from core.config import settings

logger = logging.getLogger(__name__)

QUEUE_KEY = "job_queue"

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        logger.debug("Redis connection initialised: %s", settings.REDIS_URL)
    return _redis


async def enqueue_job(job_id: str, priority: int) -> None:
    """Add job to sorted set. Higher priority = higher score = picked first."""
    r = get_redis()
    score = priority * 1e12 - time.time()
    await r.zadd(QUEUE_KEY, {job_id: score})
    logger.info("Enqueued job %s (priority=%d, score=%.0f)", job_id, priority, score)


async def dequeue_job(timeout: float = 2.0) -> str | None:
    """Pop the highest-priority job_id, or return None after timeout."""
    r = get_redis()
    result = await r.bzpopmax(QUEUE_KEY, timeout=timeout)
    if result is None:
        return None
    job_id = result[1]
    logger.info("Dequeued job %s (score=%s)", job_id, result[2])
    return job_id


async def remove_job_from_queue(job_id: str) -> None:
    r = get_redis()
    removed = await r.zrem(QUEUE_KEY, job_id)
    if removed:
        logger.info("Removed job %s from queue", job_id)
    else:
        logger.debug("Remove job %s — not found in queue (already dequeued?)", job_id)


async def set_pause_flag(job_id: str) -> None:
    """Signal a RUNNING job to pause at its next progress checkpoint."""
    r = get_redis()
    await r.set(f"pause:{job_id}", "1", ex=300)
    logger.info("Pause flag set for job %s", job_id)


async def check_pause_flag(job_id: str) -> bool:
    """Return True if a pause has been requested for this job."""
    r = get_redis()
    return await r.exists(f"pause:{job_id}") > 0


async def clear_pause_flag(job_id: str) -> None:
    """Remove the pause flag after the worker has acknowledged it."""
    r = get_redis()
    await r.delete(f"pause:{job_id}")
    logger.debug("Pause flag cleared for job %s", job_id)
