# Resumable Agentic Simulation Pipeline

A **Resumable Distributed Simulation Engine** with a LangGraph ReAct agent, PostgreSQL job state, Redis priority queue, and async workers — all running locally without Docker.

---

## Architecture

```
User
 │
 ▼
Python Client  ──►  FastAPI Server
                        │
                        ├── /agent/chat  →  LangGraph ReAct Agent (Groq LLM)
                        │                       │
                        │                       └── Tools: submit / check / aggregate / list
                        │
                        ├── /jobs        →  Job CRUD API
                        ├── /tasks       →  Task discovery API
                        │
                        ├── PostgreSQL   →  Source of truth (jobs, conversations, messages)
                        └── Redis        →  Priority job queue (sorted set)
                                │
                                ▼
                            Workers (async)
                                │
                                ▼
                        Simulation Tasks (NumPy) — 30 tasks across 6 categories
```

---

## Features

| Feature | Implementation |
|---------|---------------|
| Job lifecycle | `PENDING → QUEUED → RUNNING → COMPLETED / FAILED / CANCELLED` |
| Worker crash recovery | Lease + heartbeat system (60s lease, 10s heartbeat) |
| Retry with backoff | Exponential backoff, configurable `max_retries` |
| Priority scheduling | Redis sorted set, higher priority runs first |
| DAG execution | `depends_on` field, auto-unblocks dependents on completion |
| Progress tracking | `progress` field (0.0–1.0), updated live by workers |
| Agentic chat | LangGraph ReAct agent with conversation memory in PostgreSQL |
| Conversation management | Named conversations, full CRUD, resumable by ID |
| Task discovery | `GET /tasks` lists all 30 tasks with descriptions and default payloads |
| Interactive CLI | REPL with `/commands` for submit, status, chat, and more |

---

## Scientific Simulation Tasks (30 total)

### Monte Carlo
| Task | Key Inputs | Key Outputs |
|------|-----------|-------------|
| `monte_carlo_pi` | `iterations` | `pi_estimate`, `error` |
| `option_pricing` | `S`, `K`, `T`, `r`, `sigma`, `simulations` | `price`, `variance` |
| `random_walk` | `steps`, `particles`, `dimensions` | `mean_displacement`, `final_positions` |
| `monte_carlo_integration` | `samples`, `dimensions` | `integral`, `error` |

### Heat & Diffusion
| Task | Key Inputs | Key Outputs |
|------|-----------|-------------|
| `heat_diffusion_1d` | `grid_size`, `steps`, `diffusion_coeff` | `final_grid`, `max_temp` |
| `heat_diffusion_2d` | `grid_size`, `steps`, `diffusion_coeff` | `final_grid`, `max_temp` |
| `chemical_diffusion` | `grid_size`, `steps`, `diffusion_coeff` | `final_grid`, `mean_concentration` |
| `population_spread` | `grid_size`, `steps`, `growth_rate` | `final_grid`, `total_population` |

### Linear Algebra
| Task | Key Inputs | Key Outputs |
|------|-----------|-------------|
| `matrix_multiply` | `size` | `elapsed_ms`, `checksum` |
| `eigenvalue_decomp` | `size` | `eigenvalues`, `elapsed_ms` |
| `svd_decomposition` | `rows`, `cols` | `singular_values`, `elapsed_ms` |
| `pca_covariance` | `n_samples`, `n_features`, `n_components` | `explained_variance_ratio` |

### Physics / Kinematics
| Task | Key Inputs | Key Outputs |
|------|-----------|-------------|
| `projectile_motion` | `velocity`, `angle`, `drag_coeff` | `range`, `max_height`, `flight_time` |
| `lotka_volterra` | `alpha`, `beta`, `gamma`, `delta`, `steps` | `prey_trajectory`, `predator_trajectory` |
| `pendulum_motion` | `length`, `angle`, `steps` | `angle_trajectory`, `period` |
| `spring_mass` | `mass`, `spring_k`, `damping`, `steps` | `position_trajectory`, `energy` |

### Fluid / Network
| Task | Key Inputs | Key Outputs |
|------|-----------|-------------|
| `fluid_advection` | `grid_size`, `steps`, `velocity` | `final_field`, `mass_conservation` |
| `network_spread` | `nodes`, `edges`, `steps` | `infected_trajectory`, `peak_infected` |
| `traffic_flow` | `road_length`, `n_cars`, `steps` | `mean_velocity`, `flow_rate` |
| `forest_fire` | `grid_size`, `steps`, `p_grow`, `p_ignite` | `burned_fraction`, `final_grid` |

### Additional
| Task | Key Inputs | Key Outputs |
|------|-----------|-------------|
| `diffusion_reaction` | `grid_size`, `steps`, `Du`, `Dv`, `f`, `k` | `mean_U`, `mean_V`, `pattern_variance_V` |
| `quantum_well` | `n_points`, `well_depth`, `well_width` | `energy_levels`, `wavefunctions` |
| `brownian_motion` | `particles`, `steps`, `dimensions` | `mean_squared_displacement`, `theoretical_msd` |
| `heat_conduction_varying` | `grid_size`, `steps` | `final_grid`, `max_temp` |
| `fractal_dla` | `grid_size`, `n_particles` | `cluster_size`, `fractal_dimension` |
| `wave_propagation` | `grid_size`, `steps`, `c` | `final_field`, `energy` |
| `population_genetics` | `population`, `generations`, `alleles` | `allele_frequencies`, `heterozygosity` |
| `epidemic_sir` | `population`, `beta`, `gamma`, `steps` | `S`, `I`, `R`, `peak_infected` |
| `game_of_life` | `grid_size`, `steps` | `final_population`, `stable_at_step` |
| `financial_risk_mc` | `n_assets`, `simulations`, `horizon` | `VaR_95`, `CVaR_95`, `portfolio_return` |

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — set DATABASE_URL, REDIS_URL, GROQ_API_KEY
```

### 3. Start PostgreSQL and Redis (local)

Ensure PostgreSQL and Redis are running. Tables are created automatically on server startup.

### 4. Start the API server

```bash
uvicorn api.main:app --reload
```

### 5. Start worker(s)

```bash
python scripts/run_worker.py --concurrency 2
```

### 6. Use the client

**Interactive REPL** (no args):
```bash
python -m client.client
```
```
rasp> /tasks
rasp> /submit monte_carlo_pi iterations=500000
rasp> /status <job_id>
rasp> /list --status COMPLETED

rasp> /chat                          ← new conversation (auto-named from first message)
  [chat]> Run 3 brownian motion simulations with 200 particles
  [chat]> What are the results so far?
  [chat]> /exit

rasp> /chats                         ← list conversations: name + id
rasp> /chat <conv_id>                ← resume conversation (loads history)
rasp> /chat-rename <conv_id> My brownian study
rasp> /chat-delete <conv_id>
rasp> /quit
```

**Arg-based CLI** (non-interactive):
```bash
python -m client.client tasks                          # list all 30 tasks
python -m client.client chats [--limit 20]             # list conversations
python -m client.client submit monte_carlo_pi --iterations 1000000 --wait
python -m client.client status <job_id>
python -m client.client list [--status COMPLETED] [--limit 20]
python -m client.client cancel <job_id>
python -m client.client resume <job_id>
python -m client.client chat "Run 5 pi simulations" [--conversation-id <id>]
```

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/tasks` | List all 30 tasks with descriptions and default payloads |
| `POST` | `/jobs` | Submit a simulation job |
| `GET` | `/jobs` | List jobs (optional `?status=&limit=`) |
| `GET` | `/jobs/{id}` | Get job status, progress, result |
| `POST` | `/jobs/{id}/cancel` | Cancel a queued or running job |
| `POST` | `/jobs/{id}/resume` | Re-queue a failed or cancelled job |
| `POST` | `/agent/chat` | Chat with the simulation agent |
| `GET` | `/agent/conversations` | List conversations (name, id, created_at) |
| `GET` | `/agent/conversations/{id}` | Get conversation + full message history |
| `PATCH` | `/agent/conversations/{id}` | Rename a conversation |
| `DELETE` | `/agent/conversations/{id}` | Delete a conversation (cascades messages) |
| `GET` | `/health` | Health check |

### Task discovery

```
GET /tasks
→ {
    "tasks": [
      {"name": "monte_carlo_pi", "description": "Estimate π via Monte Carlo sampling.", "default_payload": {"iterations": 1000000}},
      ...
    ],
    "total": 30
  }
```

### Submit job example

```json
POST /jobs
{
  "task_name": "monte_carlo_pi",
  "payload": {"iterations": 1000000},
  "priority": 8,
  "max_retries": 3,
  "depends_on": []
}
```

### Agent chat

```json
POST /agent/chat
{
  "message": "Run 5 monte carlo pi simulations with 500k iterations each and average the results",
  "conversation_id": null
}
```

Response — only the assistant reply, never the full history:
```json
{
  "conversation_id": "3f2a...",
  "reply": "I've submitted 5 Monte Carlo π estimation jobs...",
  "job_ids_referenced": ["uuid1", "uuid2", "uuid3", "uuid4", "uuid5"]
}
```

Conversation is auto-named from the first 20 chars of the first message. Resume it by passing `conversation_id` in subsequent requests.

### Conversation management

```
GET  /agent/conversations
→ [{"id": "3f2a...", "name": "Run 5 monte carlo pi", "created_at": "..."}]

GET  /agent/conversations/3f2a...
→ {"id": "...", "name": "...", "created_at": "...", "messages": [
     {"id": "...", "role": "user",      "text": "Run 5 monte carlo...", "created_at": "..."},
     {"id": "...", "role": "assistant", "text": "I've submitted...",    "created_at": "..."}
   ]}

PATCH  /agent/conversations/3f2a...  {"name": "My π study"}
DELETE /agent/conversations/3f2a...
```

---

## DAG Execution

Submit jobs with dependencies to build computation graphs:

```python
from client.client import SimulationClient
c = SimulationClient()

job1 = c.submit_job("monte_carlo_pi", {"iterations": 500_000})
job2 = c.submit_job("monte_carlo_pi", {"iterations": 500_000})

# stays PENDING until job1 and job2 are both COMPLETED
agg = c.submit_job(
    "monte_carlo_pi",
    {"iterations": 100},
    depends_on=[job1["id"], job2["id"]],
)
```

---

## Correctness Guarantees

- **Crash recovery**: The scheduler runs every 30s and re-queues any `RUNNING` job whose `lease_expiry` has passed (worker crashed).
- **Exactly-once delivery**: A job transitions to `RUNNING` only after being dequeued and claimed with a worker ID.
- **Retry**: On failure, `retry_count` increments and the job is re-enqueued with exponential backoff (`5s * 2^n`). After `max_retries` the job is marked `FAILED`.

---

## Project Structure

```
api/
  main.py            FastAPI app factory, startup, CORS
  routes_jobs.py     /jobs CRUD endpoints
  routes_agent.py    /agent/chat + conversation CRUD endpoints
  routes_tasks.py    /tasks discovery endpoint
core/
  config.py          pydantic-settings (.env)
  db.py              SQLAlchemy async engine + session
  redis_client.py    Redis connection + queue helpers
models/              SQLAlchemy ORM (job, dependency, conversation, message)
schemas/             Pydantic request/response schemas
services/
  job_service.py     submit, get, cancel, resume, list
  scheduler.py       lease-expiry requeue loop (background)
  dag_executor.py    post-completion DAG unblocking
workers/
  worker.py          async worker loop
tasks/
  registry.py        TASK_REGISTRY + TASK_METADATA (30 tasks)
  monte_carlo/       pi_estimation, option_pricing, random_walk, integration
  heat_diffusion/    diffusion_1d, diffusion_2d, chemical, population_spread
  linear_algebra/    matrix_multiply, eigenvalues, svd, pca
  physics/           projectile, lotka_volterra, pendulum, spring_mass
  fluid_network/     fluid_advection, network_spread, traffic_flow, forest_fire
  additional/        10 tasks (brownian, epidemic, quantum_well, ...)
agent/
  tools.py           LangGraph tool functions (submit/check/aggregate/list)
  planner.py         create_react_agent with Groq LLM
client/
  client.py          HTTP client + interactive REPL + arg-based CLI
scripts/
  run_worker.py      entry point: python scripts/run_worker.py [--concurrency N]
```
