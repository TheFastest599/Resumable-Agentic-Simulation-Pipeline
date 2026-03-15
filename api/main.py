import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.db import create_all_tables

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up — creating tables...")
    await create_all_tables()

    from services.scheduler import run_scheduler
    scheduler_task = asyncio.create_task(run_scheduler())
    logger.info("Scheduler started.")

    yield

    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass
    logger.info("Shutdown complete.")


app = FastAPI(
    title="Resumable Agentic Simulation Pipeline",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.routes_jobs import router as jobs_router  # noqa: E402
from api.routes_agent import router as agent_router  # noqa: E402
from api.routes_tasks import router as tasks_router  # noqa: E402

app.include_router(jobs_router)
app.include_router(agent_router)
app.include_router(tasks_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
