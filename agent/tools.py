"""
LangGraph tool definitions for the simulation agent.

Tools receive db and redis via module-level context variables set by planner.py
before invoking the agent, avoiding global mutable state leaks across requests.
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
async def submit_simulation(task_name: str, payload_json: str, conversation_id: str) -> str:
    """
    Submit a scientific simulation job.

    Args:
        task_name: One of: monte_carlo_pi, random_walk, heat_diffusion, matrix_multiply, option_pricing
        payload_json: JSON string of task parameters, e.g. '{"iterations": 1000000}'
        conversation_id: The current conversation ID (UUID string)

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

    req = JobSubmitRequest(task_name=task_name, payload=payload)
    job = await submit_job(db, redis, req)
    return json.dumps({"job_id": str(job.id), "status": job.status, "task_name": job.task_name})


@tool
async def check_job_status(job_id: str) -> str:
    """
    Check the current status of a simulation job (non-blocking snapshot).

    Args:
        job_id: UUID string of the job

    Returns:
        JSON string with status, progress (0–1), and result if completed.
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
async def aggregate_results(job_ids_json: str) -> str:
    """
    Aggregate numeric results from multiple completed jobs.

    Args:
        job_ids_json: JSON array of job ID strings, e.g. '["uuid1", "uuid2"]'

    Returns:
        JSON string with per-job results and averaged numeric fields.
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


@tool
async def list_recent_jobs(conversation_id: str) -> str:
    """
    List recent simulation jobs associated with this conversation.

    Args:
        conversation_id: UUID string of the conversation

    Returns:
        JSON array of recent jobs with id, task_name, status, and progress.
    """
    from services.job_service import list_jobs_for_conversation

    db, _, _ = _get_ctx()
    try:
        cid = uuid.UUID(conversation_id)
    except ValueError:
        return json.dumps({"error": f"Invalid conversation_id: {conversation_id}"})

    jobs = await list_jobs_for_conversation(db, cid)
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


ALL_TOOLS = [submit_simulation, check_job_status, aggregate_results, list_recent_jobs]
