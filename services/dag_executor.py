import logging
import uuid

from sqlalchemy import select

from core.db import AsyncSessionLocal
from core.redis_client import enqueue_job
from models.dependency import JobDependency
from models.job import Job

logger = logging.getLogger(__name__)


async def check_and_unblock(completed_job_id: uuid.UUID) -> None:
    """
    After a job completes, find all jobs that depend on it.
    For each, if ALL its dependencies are now COMPLETED, enqueue it.
    """
    async with AsyncSessionLocal() as db:
        # Find jobs that have completed_job_id as a dependency
        stmt = select(JobDependency).where(
            JobDependency.depends_on_job_id == completed_job_id
        )
        result = await db.execute(stmt)
        edges = result.scalars().all()

        for edge in edges:
            dependent_job_id = edge.job_id

            # Fetch the dependent job
            dependent_job = await db.get(Job, dependent_job_id)
            if dependent_job is None or dependent_job.status != "PENDING":
                continue

            # Check if ALL dependencies of this job are COMPLETED
            all_deps_stmt = select(JobDependency).where(
                JobDependency.job_id == dependent_job_id
            )
            all_deps_result = await db.execute(all_deps_stmt)
            all_deps = all_deps_result.scalars().all()

            dep_job_ids = [d.depends_on_job_id for d in all_deps]
            if not dep_job_ids:
                continue

            dep_jobs_stmt = select(Job).where(Job.id.in_(dep_job_ids))
            dep_jobs_result = await db.execute(dep_jobs_stmt)
            dep_jobs = dep_jobs_result.scalars().all()

            all_completed = all(j.status == "COMPLETED" for j in dep_jobs)

            if all_completed:
                logger.info(
                    "All deps of job %s are COMPLETED — enqueueing.", dependent_job_id
                )
                dependent_job.status = "QUEUED"
                await db.commit()
                await enqueue_job(str(dependent_job_id), dependent_job.priority)
