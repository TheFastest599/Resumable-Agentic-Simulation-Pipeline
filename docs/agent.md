# Agent & Conversations

## Overview

The agent is an LLM-backed assistant that can submit simulation jobs, check their status, and answer questions about the pipeline. It maintains persistent conversation history in PostgreSQL.

## Tool-Loop Pattern

The agent uses a **tool loop** (not a ReAct reasoning chain). Each turn:

```
1. Build messages: [system_prompt] + history + [user_message]
2. LLM call → may return N tool calls in one response
3. Execute ALL tool calls (in parallel if the model supports it)
4. Append tool results to messages
5. LLM call → final text response (no tool calls)
6. Save reply, return to user
```

Max 8 steps (`MAX_STEPS = 8`) to prevent runaway loops.

This is equivalent to the Vercel AI SDK's `ToolLoopAgent` — fewer LLM calls than ReAct (which does one LLM call per tool).

## Model

```python
ChatGroq(
    model="openai/gpt-oss-120b",
    api_key=GROQ_API_KEY,
    max_tokens=3000,
    reasoning_effort="medium",
)
```

Served via [Groq API](https://console.groq.com). Change the model in `agent/planner.py → _get_llm()`.

## Tools (4 total)

All tools read `db`, `redis`, and `conversation_id` from `ContextVar` — no parameters needed for these.

### `submit_simulation(task_name, payload_json, depends_on_json)`
Submits a job. `depends_on_json` is a JSON array of job ID strings — the job stays `PENDING` until all listed jobs complete. Defaults to `"[]"` (no dependencies). Returns `{job_id, status, task_name}`.

### `check_job_status(job_id)`
Returns `{job_id, task_name, status, progress, error, worker_id}`.
**Does not return the result dict** — keeps token usage low. Full result available via `GET /jobs/{id}`.

### `list_recent_jobs()`
Lists jobs associated with the current conversation. If a `conversation_id` is active, calls `list_jobs(conversation_id=conv_id, limit=1000)` to return all jobs submitted in this conversation; otherwise falls back to the 20 most recent jobs globally.
Returns `[{job_id, task_name, status, progress, error}]`.

### `aggregate_results(job_ids_json)`
Takes a JSON array of job IDs, returns `{jobs: [...], completed_count}`.
Does not return result data — metadata only.

## Context Injection

Tools need `db`, `redis`, and `conversation_id` at runtime but can't receive them as LLM parameters. They're injected via Python's `ContextVar`:

```python
# In planner.py, before invoking the agent:
_db_ctx.set(db)
_redis_ctx.set(redis)
_conv_id_ctx.set(conversation_id)

# In tools.py:
db, redis, conv_id = _db_ctx.get(), _redis_ctx.get(), _conv_id_ctx.get()
```

This avoids global state and is safe for concurrent async requests.

## System Prompt

The system prompt (in `agent/planner.py → SYSTEM_PROMPT`) defines:
- All 30 available task names and their payload schemas
- Rules for parallel vs sequential job submission:
  - Independent jobs → submit all in one response (parallel tool calls, no `depends_on`)
  - Sequential workflow (e.g. "run X then Y") → submit X first, then submit Y with `depends_on_json='["<X_job_id>"]'`
- Always include every job ID in the reply (`QUEUED` or `PENDING` for DAG-blocked jobs)
- Don't poll after submitting

Passed as `SystemMessage` at the head of every `messages` list.

## Conversation Management

### Storage

```
Conversation
  id          UUID (PK)
  name        String(50), nullable — auto-set from first message
  created_at  timestamp

Message
  id                UUID (PK)
  conversation_id   UUID (FK → Conversation)
  role              "user" | "assistant"
  content           JSONB {"text": "..."}
  related_job_ids   ARRAY of strings (job UUIDs mentioned in reply)
  created_at        timestamp
```

### Auto-naming

When the first message in a conversation is saved, the conversation name is set to the first 20 characters of the user message:

```python
conv.name = message[:20].strip()
```

### History Window

Only the last **8 messages** are sent to the LLM per turn to limit token usage.

### related_job_ids

After each agent reply, UUIDs are extracted via regex and stored on the assistant message. This powers `list_recent_jobs()` — it looks up messages for the conversation and collects their `related_job_ids`.

## DAG Decomposition

The agent can decompose natural-language workflow requests into a DAG of dependent jobs using the `depends_on_json` parameter of `submit_simulation`.

**Example turn:**
```
User: "Run a Monte Carlo π estimate first, then once it's done run a matrix multiply"

Agent tool calls (sequential — must get job_id_A before submitting B):
  1. submit_simulation("monte_carlo_pi", '{"iterations": 1000000}', "[]")
     → {"job_id": "job_id_A", "status": "QUEUED", ...}

  2. submit_simulation("matrix_multiply", '{"size": 512}', '["job_id_A"]')
     → {"job_id": "job_id_B", "status": "PENDING", ...}

Agent reply:
  "Submitted two jobs:
   - monte_carlo_pi → job_id_A (QUEUED)
   - matrix_multiply → job_id_B (PENDING — starts automatically when job_id_A completes)"
```

The DAG infrastructure (`JobDependency` table + `check_and_unblock()` in `services/dag_executor.py`) handles the rest — no polling needed.

## Chat Endpoints

There are two ways to call the agent, suited to different clients:

| Endpoint | Transport | Used by |
|----------|-----------|---------|
| `POST /agent/chat` | Plain HTTP (blocks until reply) | Python CLI client |
| `POST /agent/chat/stream` | Server-Sent Events (streams tokens) | Next.js web client |

Both accept the same request body (`message`, optional `conversation_id`). The blocking endpoint returns the full reply as JSON once the agent finishes. The streaming endpoint starts emitting events immediately.

### SSE event protocol (`/agent/chat/stream`)

Each event is a JSON object on a `data:` line:

```
data: {"type": "token", "content": "Job submitted"}

data: {"type": "tool_start", "name": "submit_simulation", "input": {"task_name": "monte_carlo_pi", "payload_json": "{\"iterations\": 1000000}"}}

data: {"type": "tool_end", "name": "submit_simulation", "output": "{\"job_id\": \"...\", \"status\": \"QUEUED\"}"}

data: {"type": "done", "conversation_id": "...", "job_ids": ["..."]}

data: {"type": "error", "message": "..."}
```

The web client consumes this with `fetch` + `ReadableStream` (not `EventSource`, which doesn't support POST bodies). On `token` it appends to the current assistant message; on `tool_start`/`tool_end` it shows/hides live tool-call indicator chips; on `done` it sets the conversation ID and invalidates TanStack Query caches.

## Source Files

| Concern | File |
|---------|------|
| Agent logic & tool loop | `agent/planner.py` |
| Tool definitions | `agent/tools.py` |
| Chat + conversation routes | `api/routes_agent.py` |
| Conversation model | `models/conversation.py` |
| Message model | `models/message.py` |
| Request/response schemas | `schemas/agent.py` |
