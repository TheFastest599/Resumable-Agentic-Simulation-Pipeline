# API Reference

Base URL: `http://localhost:8000`
Auth: None
Content-Type: `application/json`

---

## Health

### `GET /health`
Returns `{"status": "ok"}`.

---

## Jobs

### `POST /jobs` — Submit a job
**Status:** 201 Created

**Request body:**
```json
{
  "task_name": "monte_carlo_pi",
  "payload": {"iterations": 1000000},
  "priority": 5,
  "max_retries": 3,
  "depends_on": []
}
```

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `task_name` | string | required | Must match a key in the task registry |
| `payload` | object | `{}` | Task-specific parameters (see tasks.md) |
| `priority` | int | 5 | 1–10, higher runs first |
| `max_retries` | int | 3 | ≥ 0 |
| `depends_on` | UUID[] | `[]` | Job IDs that must complete first (DAG) |
| `conversation_id` | UUID | null | Set automatically when submitted via agent |

**Response:** `JobResponse` (see schema below)

---

### `GET /jobs` — List jobs

**Query params:**
- `status` (optional) — filter by status string (e.g. `QUEUED`, `RUNNING`, `COMPLETED`)
- `conversation_id` (optional) — filter to jobs submitted within a specific conversation
- `page` (default: 1) — page number; page size is 20
- `limit` (default: 20)

**Response:** `JobSummary` objects — `payload` and `result` fields are **excluded** (use `GET /jobs/{id}` for full data).
```json
{
  "jobs": [JobSummary, ...],
  "total": 42
}
```

`total` reflects the true count across all pages (useful for pagination UI).

---

### `GET /jobs/{job_id}` — Get job

**Response:** `JobResponse` or 404

---

### `POST /jobs/{job_id}/cancel` — Cancel a job

Removes from Redis queue and sets `status=CANCELLED`.
Has no effect if already COMPLETED, CANCELLED, or FAILED.

**Response:** Updated `JobResponse`

---

### `POST /jobs/{job_id}/pause` — Pause a job

Two behaviours depending on current state:
- **QUEUED** — removes from Redis immediately, sets `status=PAUSED`.
- **RUNNING** — sets a Redis pause flag; the worker catches it at the next `progress_cb` call and sets `status=PAUSED`. The job's `progress` value is preserved.

Has no effect if already PAUSED, COMPLETED, CANCELLED, or FAILED.

**Response:** Updated `JobResponse`

---

### `POST /jobs/{job_id}/resume` — Resume a job

Re-enqueues a job in PENDING, FAILED, CANCELLED, or PAUSED state.
Resets `retry_count` to 0. A paused job re-runs from scratch (task functions are not mid-computation resumable).

**Response:** Updated `JobResponse`

---

### JobResponse Schema

Returned by `POST /jobs` and `GET /jobs/{id}` (includes all fields):

```json
{
  "id": "uuid",
  "task_name": "monte_carlo_pi",
  "payload": {"iterations": 1000000},
  "status": "COMPLETED",
  "priority": 5,
  "progress": 1.0,
  "result": {"pi_estimate": 3.14159, "error": 0.00001, "iterations": 1000000},
  "error": null,
  "retry_count": 0,
  "max_retries": 3,
  "worker_id": "worker-1",
  "conversation_id": "uuid or null",
  "created_at": "2026-03-16T10:00:00Z",
  "started_at": "2026-03-16T10:00:01Z",
  "finished_at": "2026-03-16T10:00:02Z",
  "updated_at": "2026-03-16T10:00:02Z"
}
```

| Field | Notes |
|-------|-------|
| `status` | `PENDING` \| `QUEUED` \| `RUNNING` \| `COMPLETED` \| `FAILED` \| `CANCELLED` \| `PAUSED` |
| `progress` | 0.0–1.0, updated during execution |
| `result` | Task output dict, null until COMPLETED |
| `error` | Error message string, null unless FAILED |
| `worker_id` | Which worker ran the job |
| `conversation_id` | UUID of the agent conversation that submitted this job, or null |

### JobSummary Schema

Returned by `GET /jobs` (list endpoint). Same as `JobResponse` but **without `payload` and `result`** — these JSONB fields are excluded at the query level to keep list responses fast.

---

## Agent

### `POST /agent/chat` — Chat with agent (blocking)

Used by the **Python CLI client**. Blocks until the agent finishes and returns the full reply as JSON.

**Request body:**
```json
{
  "message": "Estimate π using 5 million Monte Carlo samples",
  "conversation_id": "uuid (optional)"
}
```

- Omit `conversation_id` to start a new conversation
- Include it to continue an existing one

**Response:**
```json
{
  "conversation_id": "uuid",
  "reply": "Job submitted: monte_carlo_pi → abc123 (QUEUED)",
  "job_ids_referenced": ["abc123"]
}
```

---

### `POST /agent/chat/stream` — Streaming chat (SSE)

Used by the **Next.js web client**. Same request body as `/agent/chat`. Returns `text/event-stream` — starts emitting immediately as the LLM generates tokens.

Each event is a `data: <json>\n\n` line:

| Event type | Fields | When |
|-----------|--------|------|
| `token` | `content: str` | LLM is generating text |
| `tool_start` | `name: str, input: obj` | Tool call starting |
| `tool_end` | `name: str, output: str` | Tool call finished |
| `done` | `conversation_id: str, job_ids: str[]` | Turn complete |
| `error` | `message: str` | Unrecoverable error |

---

### `GET /agent/conversations` — List conversations

**Query params:** `limit` (default: 50), `offset` (default: 0)

**Response:**
```json
[
  {"id": "uuid", "name": "Estimate pi with 5 m", "created_at": "..."},
  ...
]
```

---

### `GET /agent/conversations/{conv_id}` — Get conversation with messages

**Response:**
```json
{
  "id": "uuid",
  "name": "Estimate pi with 5 m",
  "created_at": "...",
  "messages": [
    {"id": "uuid", "role": "user", "text": "Estimate π...", "created_at": "..."},
    {"id": "uuid", "role": "assistant", "text": "Job submitted...", "created_at": "..."}
  ]
}
```

---

### `PATCH /agent/conversations/{conv_id}` — Rename conversation

**Request body:** `{"name": "My new name"}`
**Response:** `ConversationResponse`

---

### `DELETE /agent/conversations/{conv_id}` — Delete conversation

Deletes the conversation and all its messages (CASCADE).

**Response:** `{"deleted": "uuid"}`

---

## Tasks

### `GET /tasks` — List available tasks

**Response:**
```json
[
  {
    "name": "monte_carlo_pi",
    "description": "Estimate π using Monte Carlo random sampling.",
    "default_payload": {"iterations": 1000000}
  },
  ...
]
```

Returns all 30 registered tasks with descriptions and default payloads.

---

## Error Responses

| Status | Meaning |
|--------|---------|
| 404 | Resource not found |
| 422 | Validation error (invalid request body) |
| 500 | Unhandled server error |

Error body:
```json
{"detail": "Job not found"}
```
