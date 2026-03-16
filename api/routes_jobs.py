import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

import redis.asyncio as aioredis
from core.db import get_db
from core.redis_client import get_redis
from schemas.job import JobListResponse, JobResponse, JobSubmitRequest, JobSummary
from services.job_service import (
    cancel_job,
    get_job,
    list_jobs,
    pause_job,
    resume_job,
    submit_job,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


def get_redis_dep() -> aioredis.Redis:
    return get_redis()


@router.post("", response_model=JobResponse, status_code=201)
async def create_job(
    req: JobSubmitRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
):
    job = await submit_job(db, redis, req)
    return JobResponse.model_validate(job)


@router.get("", response_model=JobListResponse)
async def read_jobs(
    status: Optional[str] = None,
    conversation_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    page: int = 1,
    db: AsyncSession = Depends(get_db),
):
    offset = (max(page, 1) - 1) * limit
    jobs, total = await list_jobs(
        db, status=status, conversation_id=conversation_id, limit=limit, offset=offset
    )
    return JobListResponse(
        jobs=[JobSummary.model_validate(j) for j in jobs],
        total=total,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def read_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    job = await get_job(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.model_validate(job)


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job_route(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
):
    job = await cancel_job(db, redis, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.model_validate(job)


@router.post("/{job_id}/pause", response_model=JobResponse)
async def pause_job_route(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
):
    job = await pause_job(db, redis, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.model_validate(job)


@router.post("/{job_id}/resume", response_model=JobResponse)
async def resume_job_route(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_dep),
):
    job = await resume_job(db, redis, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse.model_validate(job)
