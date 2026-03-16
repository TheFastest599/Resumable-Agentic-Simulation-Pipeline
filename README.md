# Resumable Agentic Simulation Pipeline

A **Resumable Distributed Simulation Engine** with a LangGraph ReAct agent, PostgreSQL job state, Redis priority queue, and async workers — all running locally without Docker.

---

## Architecture

```
User
 │
 ├── Python CLI Client  ──► HTTP (blocking)
 │
 └── Next.js Web Client ──► HTTP + SSE
              │
              ▼
        FastAPI Server
              │
              ├── POST /agent/chat        →  LLM Agent (Groq: openai/gpt-oss-120b)  [blocking]
              ├── POST /agent/chat/stream →  LLM Agent (SSE, token-by-token)        [streaming]
              │                                   │
              │                                   └── Tools: submit / check / list / aggregate
              │
              ├── POST /jobs             →  Submit job
              ├── GET  /jobs             →  List (JobSummary — no payload/result)
              ├── GET  /jobs/{id}        →  Full job detail
              ├── POST /jobs/{id}/cancel │
              ├── POST /jobs/{id}/pause  │
              ├── POST /jobs/{id}/resume │
              │
              ├── GET  /tasks            →  Task registry (30 tasks + default payloads)
              │
              ├── PostgreSQL             →  Source of truth (jobs, conversations, messages)
              └── Redis                  →  Priority queue (sorted set) + pause/cancel flags
                          │
                          ▼
                    Workers (async, N concurrent)
                          │
                          ▼
                  Simulation Tasks (NumPy) — 30 tasks across 6 categories
```

---

## Setup & Run

### 1. Prerequisites

- Python 3.11+
- PostgreSQL running locally
- Redis (or [Memurai](https://www.memurai.com/) on Windows)
- A [Groq API key](https://console.groq.com/) for the LLM agent

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env:
#   DATABASE_URL = postgresql+asyncpg://user:pass@localhost/rasp
#   REDIS_URL    = redis://localhost:6379
#   GROQ_API_KEY = gsk_...
```

### 4. Start the API server

```bash
uvicorn api.main:app --reload
# Tables are created automatically on first startup
```

### 5. Start worker(s)

```bash
python scripts/run_worker.py --concurrency 2
```

### 6. (Optional) Start the web client

```bash
cd web-client
npm install
npm run dev
# Opens at http://localhost:3000
```

### 7. Use the CLI

```bash
# Interactive REPL
python -m client.client

rasp> /tasks
rasp> /submit monte_carlo_pi iterations=500000
rasp> /status <job_id>
rasp> /chat                       # new agent conversation
  [chat]> Run 3 brownian motion sims with 200 particles
  [chat]> /exit
rasp> /chats                      # list conversations
rasp> /chat <conv_id>             # resume conversation

# Arg-based (non-interactive)
python -m client.client submit monte_carlo_pi --iterations 1000000 --wait
python -m client.client chat "Run 5 pi simulations"
```

---

## Features Implemented

### Core (Level 1)

- **Job queue & workers** — jobs submit to a Redis sorted-set queue; async workers dequeue and execute NumPy simulation tasks
- **Job state machine** — `PENDING → QUEUED → RUNNING → COMPLETED / FAILED / CANCELLED / PAUSED`; all state persisted in PostgreSQL
- **Cancel** — `POST /jobs/{id}/cancel` removes from queue (if QUEUED) or sets a Redis cancel flag (if RUNNING); workers check the flag between progress steps
- **Crash recovery** — each worker holds a 60-second lease renewed every 10 seconds via heartbeat; the background scheduler re-queues any job whose lease expired without completing

### Resilience (Level 2)

- **Exponential backoff retries** — on failure, `retry_count` increments and the job is re-enqueued after `5s × 2^n`; after `max_retries` exhausted the job is marked `FAILED`
- **Priority scheduling** — Redis sorted set scored by `-(priority × 1000 + age_ms)`; higher priority dequeues first
- **Anti-starvation** — background scheduler runs every 30 seconds and calls `ZINCRBY` to boost the score of jobs that have been waiting too long
- **Orphan / zombie recovery** — scheduler detects `RUNNING` jobs with expired leases and re-queues them
- **Pause / resume** — `POST /jobs/{id}/pause` sets a Redis flag; the worker raises `PauseSignal` at the next checkpoint, transitions to `PAUSED`, and saves progress; `POST /jobs/{id}/resume` re-queues from where it left off

### Agent (Level 3)

- **LLM agent** — LangGraph `create_react_agent` with Groq (`openai/gpt-oss-120b`); natural-language interface for submitting, monitoring, and chaining jobs
- **DAG decomposition** — the agent (or direct API) can express job dependencies via `depends_on`; `JobDependency` table + `check_and_unblock()` auto-unblocks dependents when all parents complete
- **Streaming chat** — `POST /agent/chat/stream` emits SSE events (`token`, `tool_start`, `tool_end`, `done`, `error`); the web client renders tokens in real-time with live tool-call indicators
- **Conversation persistence** — multi-turn history stored in PostgreSQL (`conversations`, `messages` tables); resumable by `conversation_id`
- **Web client** — Next.js 15 App Router UI with chat, jobs list/detail, task browser, and pagination

### Known Limitations

- Pause/resume only works for tasks that explicitly check the pause flag between iterations; tasks that run as a single NumPy call pause at the end of their current chunk
- DAG unblocking is eventually consistent — the scheduler is the fallback; `check_and_unblock()` is also called inline on job completion
- The web client assumes the API is at `http://localhost:8000` (no env-var configuration in the Next.js layer)
- `GROQ_API_KEY` is required even if you only use the job API; the server will start but `/agent/*` routes will fail without it

---

## Architectural Decisions

**Redis sorted set as the queue.** `BZPOPMAX` gives atomic pop-and-claim in a single command, eliminating any race between "peek" and "claim." The score encodes both priority and submission time so that a single sort operation determines which job to run next. The alternative (a Postgres-based queue with `SELECT FOR UPDATE SKIP LOCKED`) would work but adds lock contention and a polling loop.

**SQLAlchemy 2.0 async with asyncpg.** The server is fully async end-to-end. Using the async SQLAlchemy API means no thread-pool overhead for DB I/O, and the same event loop drives HTTP, DB, and Redis calls. The tradeoff is a steeper learning curve (sessions must be explicitly passed or injected) — solved here with FastAPI's `Depends(get_db)` pattern.

**Tool-loop agent (LangGraph ReAct) over a planner/executor split.** A ReAct loop is simpler to reason about, easier to debug (the full thought chain is visible), and well-suited to the open-ended nature of simulation requests. A separate planner step would add latency and complexity without meaningful benefit for this domain.

**ContextVar injection for db/redis into agent tools.** LangChain tool functions don't accept arbitrary keyword arguments. Rather than polluting the tool signatures or using global state, Python `ContextVar`s carry the per-request DB session, Redis client, and conversation ID into the tool functions cleanly and without thread-safety concerns.

**Two chat endpoints for two clients.** `POST /agent/chat` is a plain HTTP request/response used by the Python CLI — it blocks until the full reply is ready and returns it as JSON. `POST /agent/chat/stream` is Server-Sent Events used by the web client — it emits `token`, `tool_start`, `tool_end`, `done`, and `error` events so the UI can render the agent's reply word-by-word. The web client consumes SSE manually with `fetch` + `ReadableStream` rather than the Vercel AI SDK because the event protocol is custom; this keeps the client thin and avoids mismatched protocol adapters.

**`load_only` on list queries to skip JSONB columns.** `payload` and `result` can be large; excluding them from `GET /jobs` via SQLAlchemy `load_only` drops response size significantly at zero cost. A separate `JobSummary` Pydantic schema (no payload/result fields) enforces this at the serialization layer.

---

## Docs

| Document | Contents |
|----------|----------|
| [docs/architecture.md](docs/architecture.md) | Component diagram, data flow, module map |
| [docs/job-pipeline.md](docs/job-pipeline.md) | Full job lifecycle, lease/heartbeat, retry logic, DAG execution |
| [docs/agent.md](docs/agent.md) | Agent tools, streaming protocol, conversation persistence |
| [docs/api.md](docs/api.md) | Full API reference with request/response examples |
| [docs/tasks.md](docs/tasks.md) | All 30 simulation tasks — inputs, outputs, categories |
| [docs/queries.md](docs/queries.md) | Example natural-language queries you can send to the agent |

---

## One Thing I'd Do Differently

I'd make the job progress experience fully real-time. Currently the web client polls `GET /jobs/{id}` every 3 seconds — good enough, but you see progress jump in steps and there's always a lag before the final status appears. With more time I'd add a per-job SSE or WebSocket channel so the worker streams progress increments directly to the browser as they happen: `0.1 → 0.2 → ... → 1.0 → COMPLETED`. The infrastructure is mostly there (workers already call `progress_cb`, the SSE path exists for chat) — it just needs a Redis pub/sub fan-out and a `GET /jobs/{id}/stream` endpoint to wire it up end-to-end.
