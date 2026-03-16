# Architecture

## Overview

RASP (Resumable Agentic Simulation Pipeline) is a distributed scientific simulation engine. Users submit simulation jobs via a REST API or an AI agent chat interface. Jobs are queued in Redis, picked up by async workers, and results persisted in PostgreSQL.

## Component Diagram

```
User / Client
     │
     ├── Python CLI Client (client/client.py)  ──► HTTP / SSE
     │
     └── Next.js Web Client (web-client/)       ──► HTTP / SSE
              │
              ▼
FastAPI Server (api/main.py)
     │
     ├── POST /agent/chat        ──► LLM Agent (agent/planner.py)  [blocking, used by Python client]
     ├── POST /agent/chat/stream ──► LLM Agent (streaming SSE)     [used by web client]
     │                                    │  Groq: openai/gpt-oss-120b
     │                                    │  Tools: submit, check, list, aggregate
     │                                    └── agent/tools.py
     │
     ├── POST /jobs ──────────────────────────────────┐
     ├── GET  /jobs  (JobSummary — no payload/result) │
     ├── GET  /jobs/{id}                              │
     ├── POST /jobs/{id}/cancel                       │
     ├── POST /jobs/{id}/pause                        │
     ├── POST /jobs/{id}/resume                       │
     │                                                │
     ├── GET  /tasks ─► Task Registry (tasks/registry.py)
     │
     ├── PostgreSQL (asyncpg)          Redis (Memurai)
     │   jobs, conversations,          priority queue
     │   messages, dependencies        sorted set: job_queue
     │
     └── Background Scheduler (services/scheduler.py)
              Every 30s: recover crashed/orphaned jobs + anti-starvation boost

                   ▼
          Workers (workers/worker.py)
          python scripts/run_worker.py --concurrency N
               │
               ▼
          Task Functions (tasks/**/*)
          NumPy-based scientific simulations
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Web framework | FastAPI (async) |
| Database ORM | SQLAlchemy 2.0 async + asyncpg |
| Job queue | Redis sorted set (Memurai on Windows) |
| LLM provider | Groq API (`openai/gpt-oss-120b`) |
| LLM framework | LangChain + LangGraph |
| Simulation | NumPy |
| Web client | Next.js 15 App Router, TanStack Query, Zustand, shadcn/ui |
| Config | pydantic-settings (.env) |
| Client colors | colorama |

## Key Design Decisions

**Async-first:** FastAPI + SQLAlchemy async + asyncio workers. CPU-bound task functions run in a thread pool executor to avoid blocking the event loop.

**PostgreSQL as source of truth:** All job state (status, progress, result, retries) lives in PostgreSQL. Redis is ephemeral — if it's flushed, the scheduler re-populates the queue from DB state.

**Redis as ephemeral queue only:** Redis holds job IDs (not job data) in a sorted set. Score encodes priority and submission time. Workers pop with `BZPOPMAX` (blocking, highest score first).

**No Docker:** Runs directly on the host. Requires PostgreSQL and Redis/Memurai installed locally.

## Startup Sequence

```
python -m uvicorn api.main:app
  1. FastAPI lifespan starts
  2. create_all_tables() — creates tables if they don't exist
  3. run_scheduler() — starts background recovery loop (30s interval)
  4. Server ready to accept requests

python scripts/run_worker.py --concurrency 2
  1. create_all_tables() — idempotent
  2. worker_loop("worker-1") + worker_loop("worker-2") started
  3. Each worker blocks on dequeue_job(timeout=2s)
```

## Configuration (`.env`)

```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/simulation_engine
REDIS_URL=redis://localhost:6379/0
GROQ_API_KEY=your_key_here
```

## Source Files

| Concern | File |
|---------|------|
| App factory & lifespan | `api/main.py` |
| DB engine & session | `core/db.py` |
| Redis connection | `core/redis_client.py` |
| Config / env | `core/config.py` |
| Background scheduler | `services/scheduler.py` |
| Web client root | `web-client/src/` |
| API layer (axios) | `web-client/src/lib/api.js` |
| TanStack Query hooks | `web-client/src/lib/queries.js` |
| SSE consumer hook | `web-client/src/hooks/useStream.js` |
| Global chat state | `web-client/src/store/chatStore.js` |
