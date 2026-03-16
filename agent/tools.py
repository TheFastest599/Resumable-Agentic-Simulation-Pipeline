"""
Tool definitions for the simulation agent.

Tools receive db, redis, and conversation_id via module-level context variables
set by planner.py before invoking the agent.
"""
import json
import uuid
from contextvars import ContextVar
from typing import Any

from langchain_core.tools import tool
from sqlalchemy.ext.asyncio import AsyncSession

import redis.asyncio as aioredis

# Per-request context injected by planner.run_agent_chat
_db_ctx: ContextVar[AsyncSession] = ContextVar("_db_ctx")
_redis_ctx: ContextVar[aioredis.Redis] = ContextVar("_redis_ctx")
_conv_id_ctx: ContextVar[uuid.UUID] = ContextVar("_conv_id_ctx")


def _get_ctx():
    return _db_ctx.get(), _redis_ctx.get(), _conv_id_ctx.get()


@tool
async def submit_simulation(task_name: str, payload_json: str, depends_on_json: str = "[]") -> str:
    """
    Submit a scientific simulation job.

    Args:
        task_name: The simulation task name (e.g. monte_carlo_pi, random_walk)
        payload_json: JSON string of task parameters, e.g. '{"iterations": 1000000}'
        depends_on_json: JSON array of job_id strings this job depends on, e.g. '["uuid1"]'.
            The job stays PENDING until all listed jobs complete. Omit or pass '[]' for no dependencies.

    Returns:
        JSON string with job_id and status.
    """
    from schemas.job import JobSubmitRequest
    from services.job_service import submit_job

    db, redis, _ = _get_ctx()

    try:
        payload: dict[str, Any] = json.loads(payload_json) if payload_json else {}
    except json.JSONDecodeError:
        payload = {}

    depends_on: list[uuid.UUID] = []
    try:
        depends_on = [uuid.UUID(jid) for jid in json.loads(depends_on_json)]
    except (json.JSONDecodeError, ValueError):
        pass

    req = JobSubmitRequest(task_name=task_name, payload=payload, depends_on=depends_on)
    job = await submit_job(db, redis, req)
    return json.dumps({"job_id": str(job.id), "status": job.status, "task_name": job.task_name})


@tool
async def check_job_status(job_id: str) -> str:
    """
    Check the current status of a simulation job.

    Args:
        job_id: UUID string of the job

    Returns:
        JSON string with status and progress.
    """
    from services.job_service import get_job

    db, _, _ = _get_ctx()
    try:
        jid = uuid.UUID(job_id)
    except ValueError:
        return json.dumps({"error": f"Invalid job_id: {job_id}"})

    job = await get_job(db, jid)
    if job is None:
        return json.dumps({"error": f"Job {job_id} not found"})

    return json.dumps({
        "job_id": str(job.id),
        "task_name": job.task_name,
        "status": job.status,
        "progress": job.progress,
        "error": job.error,
        "worker_id": job.worker_id,
    })


@tool
async def list_recent_jobs() -> str:
    """
    List recent simulation jobs for the current conversation.

    Returns:
        JSON array of recent jobs with id, task_name, status, and progress.
    """
    from services.job_service import list_jobs_for_conversation

    db, _, conv_id = _get_ctx()
    jobs = await list_jobs_for_conversation(db, conv_id)
    return json.dumps([
        {
            "job_id": str(j.id),
            "task_name": j.task_name,
            "status": j.status,
            "progress": j.progress,
            "error": j.error,
        }
        for j in jobs
    ])


@tool
async def aggregate_results(job_ids_json: str) -> str:
    """
    Aggregate status of multiple jobs.

    Args:
        job_ids_json: JSON array of job ID strings, e.g. '["uuid1", "uuid2"]'

    Returns:
        JSON string with per-job status and completed count.
    """
    from services.job_service import get_job

    db, _, _ = _get_ctx()

    try:
        job_ids = json.loads(job_ids_json)
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON array"})

    results = []
    for jid_str in job_ids:
        try:
            job = await get_job(db, uuid.UUID(jid_str))
        except ValueError:
            continue
        if job:
            results.append({
                "job_id": str(job.id),
                "task_name": job.task_name,
                "status": job.status,
                "progress": job.progress,
                "error": job.error,
            })

    completed_count = sum(1 for r in results if r["status"] == "COMPLETED")
    return json.dumps({"jobs": results, "completed_count": completed_count})


ALL_TOOLS = [submit_simulation, check_job_status, aggregate_results, list_recent_jobs]
