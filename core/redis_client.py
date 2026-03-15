import redis.asyncio as aioredis

from core.config import settings

QUEUE_KEY = "job_queue"

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def enqueue_job(job_id: str, priority: int) -> None:
    """Add job to sorted set. Higher priority = higher score = picked first."""
    r = get_redis()
    import time
    # Negate priority so ZPOPMAX (highest score) picks highest priority first.
    # Use negative timestamp as tiebreaker so older jobs win.
    score = priority * 1e12 - time.time()
    await r.zadd(QUEUE_KEY, {job_id: score})


async def dequeue_job(timeout: float = 2.0) -> str | None:
    """Pop the highest-priority job_id, or return None after timeout."""
    r = get_redis()
    # BZPOPMAX blocks until an element is available or timeout expires.
    result = await r.bzpopmax(QUEUE_KEY, timeout=timeout)
    if result is None:
        return None
    # result = (key, member, score)
    return result[1]


async def remove_job_from_queue(job_id: str) -> None:
    r = get_redis()
    await r.zrem(QUEUE_KEY, job_id)
