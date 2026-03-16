# Job Pipeline

Everything about how a job moves from submission to completion.

## State Machine

```
                  submit_job()
                      │
                      ▼
                  PENDING ──────────────────────────────────────────────┐
                      │                                                  │
         (no depends_on)                                    (has depends_on — waits)
                      │                                                  │
                      ▼                                                  │
                  QUEUED ◄─────────── check_and_unblock() ◄─────────────┘
                      │               (all deps completed)
                 dequeue_job()
                      │
                      ▼
                  RUNNING
               ╱          ╲
         success          failure
           │                │
           ▼                ├── retry_count ≤ max_retries → QUEUED (retry)
       COMPLETED            │
                            └── retry_count > max_retries → FAILED

       (any state)
           │
        cancel_job()
           ▼
       CANCELLED

       QUEUED (immediate) or RUNNING (at next progress checkpoint)
           │
        pause_job()
           ▼
         PAUSED

       FAILED / CANCELLED / PENDING / PAUSED
           │
        resume_job()
           ▼
         QUEUED
```

## Redis Priority Queue

Jobs are stored in a Redis sorted set (`job_queue`).

**Score formula:**
```python
score = priority * 1e12 - time.time()
```

- Priority 10 always beats priority 1
- Within the same priority, earlier submissions have a slightly higher score (older jobs run first)
- Workers call `BZPOPMAX` — blocking pop of highest-score member

**Operations:**
- `enqueue_job(job_id, priority)` — `ZADD job_queue score job_id`
- `dequeue_job(timeout=2s)` — `BZPOPMAX job_queue 2` → returns `(key, job_id, score)`
- `remove_job_from_queue(job_id)` — `ZREM job_queue job_id` (used on cancel)

## Worker Execution

```python
# scripts/run_worker.py
worker_loop("worker-1")   # asyncio coroutine
worker_loop("worker-2")   # run concurrently via asyncio.gather()
```

Each worker loop:
1. `dequeue_job(timeout=2s)` — blocks up to 2s waiting for a job
2. `process_job(job_id, worker_id)` — full execution with error handling
3. Loop back

### process_job

1. Load job from DB — skip if not QUEUED (another worker may have picked it up)
2. Set `status=RUNNING`, `started_at`, `worker_id`, `lease_expiry=now+60s`
3. Start `_heartbeat` task (extends lease every 10s)
4. Run task in thread pool: `loop.run_in_executor(None, task_fn, payload, progress_cb)`
5. On success: `status=COMPLETED`, `result=...`, `progress=1.0`
6. On failure: increment `retry_count`, retry or set FAILED (see Retries)
7. Stop heartbeat

## Progress Tracking

Task functions receive a `progress_cb(value: float)` callback.

Since tasks run in a **thread pool** (blocking), they can't directly call async DB methods. The callback bridges via `asyncio.run_coroutine_threadsafe()`:

```python
def sync_progress(value: float) -> None:
    async def _update():
        async with AsyncSessionLocal() as progress_db:  # separate session
            j = await progress_db.get(Job, job_id)
            if j:
                j.progress = round(min(max(value, 0.0), 1.0), 4)
                await progress_db.commit()
    asyncio.run_coroutine_threadsafe(_update(), loop)
```

Progress uses a **separate DB session** to avoid conflicts with the outer `process_job` session.

## Heartbeat & Lease

- `lease_expiry` is set to `now + 60s` when a job starts RUNNING
- The `_heartbeat` coroutine extends it by 60s every 10s while the job is RUNNING
- If a worker crashes, heartbeats stop and the lease expires
- The scheduler detects this and re-queues the job

```
constants in workers/worker.py:
  LEASE_DURATION = 60      # seconds
  HEARTBEAT_INTERVAL = 10  # seconds
  BASE_RETRY_DELAY = 5     # seconds
```

## Retries with Exponential Backoff

On exception during task execution:

```python
retry_count += 1
if retry_count <= max_retries:
    delay = BASE_RETRY_DELAY * (2 ** (retry_count - 1))
    # delays: 5s, 10s, 20s, 40s, ...
    status = QUEUED
    await asyncio.sleep(delay)
    await enqueue_job(job_id, priority)
else:
    status = FAILED
    finished_at = now
```

Default `max_retries=3` means up to 3 retry attempts (4 total tries).

## Pause & Resume

Jobs can be paused via `POST /jobs/{id}/pause`.

### QUEUED jobs
Removed from Redis immediately. `status` → `PAUSED`. No worker involvement.

### RUNNING jobs
A Redis key `pause:{job_id}` (TTL 5 minutes) is set. The worker checks this flag inside `sync_progress` — the callback called by the task function on every progress update:

```python
# workers/worker.py — sync_progress (runs in executor thread)
future = asyncio.run_coroutine_threadsafe(_update(), loop)
future.result(timeout=5)   # blocks thread until async check completes
# _update() raises PauseSignal if pause:{job_id} exists in Redis
```

`PauseSignal` propagates out of `task_fn` → `run_in_executor` → `_execute_job` → `process_job`, where it's caught:

```python
except PauseSignal:
    job.status = "PAUSED"
    await db.commit()
    await clear_pause_flag(job_id_str)
```

The job's `progress` value (last written by `sync_progress` before the pause) is preserved.

**Resume**: `POST /jobs/{id}/resume` re-enqueues the job. Tasks are not mid-computation resumable — the job re-runs from scratch, but the previous `progress` value gives context on how far it got.

---

## Background Scheduler

Runs every 30 seconds (`services/scheduler.py`).

### Recovery 1: Crashed RUNNING jobs
```sql
SELECT * FROM jobs
WHERE status = 'RUNNING' AND lease_expiry < now()
```
→ Sets `status=QUEUED`, clears `worker_id` and `lease_expiry`, re-enqueues.

### Recovery 3: Anti-starvation (score aging)

Low-priority jobs can wait indefinitely if high-priority jobs keep arriving. Every scheduler tick, jobs that have been QUEUED for more than `AGE_THRESHOLD` (60s) get their Redis score boosted:

```python
AGE_THRESHOLD = 60          # seconds before aging kicks in
AGE_BOOST_PER_INTERVAL = 0.5e12  # ~half a priority level per 30s tick
```

After 10 intervals (5 minutes), a priority-1 job has gained `5e12` — equivalent to 5 extra priority levels — making it competitive with priority-6 jobs. No low-priority job waits forever.

### Recovery 2: Orphaned PENDING/QUEUED jobs
Jobs that are PENDING or QUEUED in the DB but **not present in the Redis sorted set** (e.g., server crash between DB commit and Redis enqueue).

Excludes jobs with unmet dependencies:
```sql
SELECT * FROM jobs
WHERE status IN ('PENDING', 'QUEUED')
AND id NOT IN (
    SELECT jd.job_id FROM job_dependencies jd
    JOIN jobs dep ON dep.id = jd.depends_on_job_id
    WHERE dep.status != 'COMPLETED'
)
```
→ Re-enqueues any not found in Redis.

## DAG Execution

Jobs can declare dependencies via `depends_on: [uuid, ...]` at submission.

```
Job A (no deps) → QUEUED immediately
Job B (depends_on: [A]) → stays PENDING until A completes
Job C (depends_on: [A, B]) → stays PENDING until both complete
```

**How it works:**
1. `JobDependency` rows are inserted at submission time (edges in a dependency graph)
2. When a job completes, `check_and_unblock(completed_job_id)` is called
3. It finds all jobs that depend on the completed job
4. For each: if ALL their dependencies are now COMPLETED → set QUEUED + enqueue

```python
# services/dag_executor.py
async def check_and_unblock(completed_job_id: uuid.UUID) -> None: ...
```

## Source Files

| Concern | File |
|---------|------|
| Job CRUD + pause/resume | `services/job_service.py` |
| Job model | `models/job.py` |
| Dependency model | `models/dependency.py` |
| Worker loop + PauseSignal | `workers/worker.py` |
| Worker entry point | `scripts/run_worker.py` |
| Redis queue + pause flags | `core/redis_client.py` |
| Scheduler + anti-starvation | `services/scheduler.py` |
| DAG unblocking | `services/dag_executor.py` |
