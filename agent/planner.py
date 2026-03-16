"""
Tool-loop agent backed by Groq LLM.
Manages conversation memory in PostgreSQL.

Pattern: LLM decides tools → execute ALL in parallel → feed results back → repeat
until no more tool calls or max steps reached. Typically 2 LLM calls per turn.
"""
import json
import logging
import re
import uuid
from typing import Any

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_groq import ChatGroq
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import redis.asyncio as aioredis

from agent.tools import ALL_TOOLS, _conv_id_ctx, _db_ctx, _redis_ctx
from core.config import settings
from models.conversation import Conversation
from models.message import Message

logger = logging.getLogger(__name__)

MAX_STEPS = 8

SYSTEM_PROMPT = """You are a scientific simulation assistant.
You can submit simulation jobs, check their status, aggregate results, and list recent jobs.

Available simulation tasks (30 total):

MONTE CARLO SIMULATIONS:
- monte_carlo_pi: Estimate π. Payload: {"iterations": <int>}
- option_pricing: European option pricing. Payload: {"S": <float>, "K": <float>, "T": <float>, "r": <float>, "sigma": <float>, "simulations": <int>}
- random_walk: Particle random walk. Payload: {"steps": <int>, "particles": <int>, "dimensions": <1|2|3>}
- monte_carlo_integration: Numerical integration. Payload: {"samples": <int>, "function": <"sin"|"cos"|"exp"|"x2"|"x3"|"sqrt">, "a": <float>, "b": <float>}

HEAT & DIFFUSION:
- heat_diffusion_1d: 1D heat diffusion. Payload: {"n_points": <int>, "steps": <int>, "diffusion_coeff": <float>}
- heat_diffusion_2d: 2D heat diffusion. Payload: {"grid_size": <int>, "steps": <int>, "diffusion_coeff": <float>}
- chemical_diffusion: Chemical species diffusion. Payload: {"grid_size": <int>, "steps": <int>, "diffusion_coeff": <float>}
- population_spread: Fisher-KPP population spread. Payload: {"grid_size": <int>, "steps": <int>, "growth_rate": <float>}

LINEAR ALGEBRA:
- matrix_multiply: Matrix multiplication benchmark. Payload: {"size": <int>}
- eigenvalue_decomp: Eigenvalue decomposition. Payload: {"size": <int>}
- svd_decomposition: SVD decomposition. Payload: {"rows": <int>, "cols": <int>}
- pca_covariance: PCA / covariance analysis. Payload: {"n_samples": <int>, "n_features": <int>, "n_components": <int>}

PHYSICS / KINEMATICS:
- projectile_motion: Projectile with drag. Payload: {"initial_velocity": <float>, "angle_deg": <float>, "drag_coeff": <float>}
- lotka_volterra: Predator-prey model. Payload: {"prey_initial": <float>, "predator_initial": <float>, "steps": <int>}
- pendulum_motion: Damped pendulum. Payload: {"length": <float>, "damping": <float>, "initial_angle_deg": <float>, "steps": <int>}
- spring_mass: Spring-mass system. Payload: {"mass": <float>, "spring_constant": <float>, "damping": <float>, "steps": <int>}

FLUID / NETWORK:
- fluid_advection: Particle advection in 2D flow. Payload: {"n_particles": <int>, "steps": <int>}
- network_spread: SIR spread on random graph. Payload: {"n_nodes": <int>, "infection_prob": <float>, "recovery_prob": <float>, "steps": <int>}
- traffic_flow: Nagel-Schreckenberg traffic CA. Payload: {"road_length": <int>, "n_vehicles": <int>, "steps": <int>}
- forest_fire: Forest fire / percolation CA. Payload: {"grid_size": <int>, "p_tree": <float>, "steps": <int>}

ADDITIONAL:
- diffusion_reaction: Gray-Scott reaction-diffusion. Payload: {"grid_size": <int>, "steps": <int>, "f": <float>, "k": <float>}
- quantum_well: Quantum particle in 1D well. Payload: {"n_points": <int>, "well_depth": <float>, "well_width": <float>}
- brownian_motion: Brownian motion / stochastic process. Payload: {"n_particles": <int>, "steps": <int>, "diffusion_coeff": <float>, "dimensions": <1|2|3>}
- heat_conduction_varying: 1D heat with varying conductivity. Payload: {"n_points": <int>, "steps": <int>, "conductivity_profile": <"step"|"linear"|"gaussian">}
- fractal_dla: Diffusion-limited aggregation fractal. Payload: {"grid_size": <int>, "n_particles": <int>}
- wave_propagation: Wave equation simulation. Payload: {"dimensions": <1|2>, "grid_size": <int>, "steps": <int>, "wave_speed": <float>}
- population_genetics: Wright-Fisher allele drift. Payload: {"population_size": <int>, "generations": <int>, "initial_allele_freq": <float>, "n_replicates": <int>}
- epidemic_sir: SIR/SEIR epidemic model. Payload: {"model": <"SIR"|"SEIR">, "population": <int>, "beta": <float>, "gamma": <float>, "steps": <int>}
- game_of_life: Conway's Game of Life. Payload: {"grid_size": <int>, "steps": <int>, "pattern": <"random"|"glider"|"blinker">, "initial_density": <float>}
- financial_risk_mc: Portfolio risk Monte Carlo (VaR/CVaR). Payload: {"n_assets": <int>, "n_scenarios": <int>, "horizon_days": <int>, "confidence": <float>}

Rules:
- When the user asks for multiple independent jobs, call submit_simulation for ALL of them in ONE response using parallel tool calls (no depends_on).
- When the user asks for a sequential workflow (e.g. "run X then Y", "after X finishes do Y"), submit X first (no depends_on), get its job_id, then submit Y with depends_on_json='["<X_job_id>"]'. Y will automatically start when X completes.
- Submit each job EXACTLY ONCE. Never re-submit.
- IMPORTANT: After submitting, you MUST include every job_id from the tool results in your reply. Format each as: task_name → job_id (QUEUED or PENDING). A PENDING job is waiting on a dependency. Never omit job IDs.
- Do NOT call check_job_status after submitting — jobs run asynchronously.
- Only call check_job_status when the user explicitly asks.
- Do not fabricate results. Keep responses concise.
"""

_llm = None
_llm_with_tools = None


def _get_llm():
    global _llm, _llm_with_tools
    if _llm is None:
        _llm = ChatGroq(
            model="openai/gpt-oss-20b",
            api_key=settings.GROQ_API_KEY,
            max_tokens=3000,
            max_retries=2,
            reasoning_effort="medium",
        )
        _llm_with_tools = _llm.bind_tools(ALL_TOOLS)
    return _llm_with_tools


# Build a name→callable lookup for tool execution
_TOOL_MAP = {t.name: t for t in ALL_TOOLS}


async def _execute_tool_calls(tool_calls: list[dict]) -> list[ToolMessage]:
    """Execute all tool calls and return ToolMessages."""
    results = []
    for tc in tool_calls:
        tool_fn = _TOOL_MAP.get(tc["name"])
        if tool_fn is None:
            results.append(ToolMessage(
                content=json.dumps({"error": f"Unknown tool: {tc['name']}"}),
                tool_call_id=tc["id"],
            ))
            continue
        try:
            output = await tool_fn.ainvoke(tc["args"])
            results.append(ToolMessage(
                content=output if isinstance(
                    output, str) else json.dumps(output),
                tool_call_id=tc["id"],
            ))
        except Exception as e:
            results.append(ToolMessage(
                content=json.dumps({"error": str(e)}),
                tool_call_id=tc["id"],
            ))
    return results


async def _load_history(db: AsyncSession, conversation_id: uuid.UUID, max_messages: int = 8) -> list:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .limit(max_messages)
    )
    result = await db.execute(stmt)
    messages = result.scalars().all()

    history = []
    for msg in messages:
        text = msg.content.get("text", "") if isinstance(
            msg.content, dict) else str(msg.content)
        if msg.role == "user":
            history.append(HumanMessage(content=text))
        elif msg.role == "assistant":
            history.append(AIMessage(content=text))
    return history


async def _ensure_conversation(db: AsyncSession, conversation_id: uuid.UUID) -> None:
    existing = await db.get(Conversation, conversation_id)
    if existing is None:
        db.add(Conversation(id=conversation_id))
        await db.commit()


async def _save_message(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    role: str,
    content: str,
    related_job_ids: list[str] | None = None,
) -> None:
    msg = Message(
        conversation_id=conversation_id,
        role=role,
        content={"text": content},
        related_job_ids=related_job_ids or [],
    )
    db.add(msg)
    await db.commit()


def _extract_job_ids(text: str) -> list[str]:
    return re.findall(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        text,
        re.IGNORECASE,
    )


async def _tool_loop(messages: list) -> str:
    """
    Simple tool loop: LLM → execute all tool calls → LLM → repeat.
    Stops when LLM returns no tool calls or MAX_STEPS reached.
    """
    llm = _get_llm()

    for _ in range(MAX_STEPS):
        response: AIMessage = await llm.ainvoke(messages)
        messages.append(response)

        # No tool calls → final text response
        if not response.tool_calls:
            raw = response.content
            if isinstance(raw, str):
                return raw
            if isinstance(raw, list):
                return " ".join(
                    p.get("text", "") for p in raw if isinstance(p, dict)
                )
            return str(raw)

        # Execute ALL tool calls in parallel, append results
        tool_results = await _execute_tool_calls(response.tool_calls)
        messages.extend(tool_results)

    return "I reached the maximum number of steps. Please try a simpler request."


async def run_agent_chat(
    message: str,
    conversation_id: uuid.UUID,
    db: AsyncSession,
    redis: aioredis.Redis,
) -> tuple[str, list[str]]:
    """
    Run the tool-loop agent for one conversation turn.
    Returns (reply_text, referenced_job_ids).
    """
    db_token = _db_ctx.set(db)
    redis_token = _redis_ctx.set(redis)
    conv_token = _conv_id_ctx.set(conversation_id)

    try:
        await _ensure_conversation(db, conversation_id)
        history = await _load_history(db, conversation_id)

        if not history:
            conv = await db.get(Conversation, conversation_id)
            if conv and conv.name is None:
                conv.name = message[:20].strip()
                await db.commit()

        messages: list[Any] = (
            [SystemMessage(content=SYSTEM_PROMPT)]
            + history
            + [HumanMessage(content=message)]
        )

        reply = await _tool_loop(messages)
        reply = reply.strip() or "I was unable to process your request."

        await _save_message(db, conversation_id, "user", message)
        job_ids = _extract_job_ids(reply)
        await _save_message(db, conversation_id, "assistant", reply, related_job_ids=job_ids)

        return reply, job_ids

    except Exception as e:
        logger.exception("Agent error: %s", e)
        return f"An error occurred: {e}", []

    finally:
        _db_ctx.reset(db_token)
        _redis_ctx.reset(redis_token)
        _conv_id_ctx.reset(conv_token)


async def stream_agent_chat(
    message: str,
    conversation_id: uuid.UUID,
    db: AsyncSession,
    redis: aioredis.Redis,
):
    """
    Streaming tool-loop agent. Yields SSE-formatted lines.

    Event types:
      {"type": "token",      "content": "..."}
      {"type": "tool_start", "name": "...", "input": {...}}
      {"type": "tool_end",   "name": "...", "output": "..."}
      {"type": "done",       "conversation_id": "...", "job_ids": [...]}
      {"type": "error",      "message": "..."}
    """
    def _sse(payload: dict) -> str:
        return f"data: {json.dumps(payload)}\n\n"

    db_token = _db_ctx.set(db)
    redis_token = _redis_ctx.set(redis)
    conv_token = _conv_id_ctx.set(conversation_id)

    try:
        await _ensure_conversation(db, conversation_id)
        history = await _load_history(db, conversation_id)

        if not history:
            conv = await db.get(Conversation, conversation_id)
            if conv and conv.name is None:
                conv.name = message[:20].strip()
                await db.commit()

        messages: list[Any] = (
            [SystemMessage(content=SYSTEM_PROMPT)]
            + history
            + [HumanMessage(content=message)]
        )

        llm = _get_llm()
        reply_parts: list[str] = []

        for _ in range(MAX_STEPS):
            # Stream this LLM call
            tool_calls_acc: list[dict] = []
            async for chunk in llm.astream(messages):
                # Accumulate tool calls from chunks
                if chunk.tool_call_chunks:
                    for tc_chunk in chunk.tool_call_chunks:
                        if tc_chunk.get("index") is not None:
                            idx = tc_chunk["index"]
                            while len(tool_calls_acc) <= idx:
                                tool_calls_acc.append(
                                    {"name": "", "args": "", "id": ""})
                            if tc_chunk.get("name"):
                                tool_calls_acc[idx]["name"] = tc_chunk["name"]
                            if tc_chunk.get("id"):
                                tool_calls_acc[idx]["id"] = tc_chunk["id"]
                            if tc_chunk.get("args"):
                                tool_calls_acc[idx]["args"] += tc_chunk["args"]

                # Stream text tokens
                text = chunk.content if isinstance(chunk.content, str) else ""
                if text:
                    reply_parts.append(text)
                    yield _sse({"type": "token", "content": text})

            # If no tool calls, we're done
            if not tool_calls_acc or not tool_calls_acc[0]["name"]:
                break

            # Parse accumulated tool call args from strings to dicts
            parsed_calls = []
            for tc in tool_calls_acc:
                try:
                    args = json.loads(tc["args"]) if isinstance(
                        tc["args"], str) else tc["args"]
                except json.JSONDecodeError:
                    args = {}
                parsed_calls.append(
                    {"name": tc["name"], "args": args, "id": tc["id"]})

            # Build the AI message with tool calls for message history
            ai_msg = AIMessage(content="", tool_calls=[
                {"name": tc["name"], "args": tc["args"], "id": tc["id"]}
                for tc in parsed_calls
            ])
            messages.append(ai_msg)

            # Emit tool_start events
            for tc in parsed_calls:
                yield _sse({"type": "tool_start", "name": tc["name"], "input": tc["args"]})

            # Execute all tool calls
            tool_results = await _execute_tool_calls(parsed_calls)
            messages.extend(tool_results)

            # Emit tool_end events
            for tc, result in zip(parsed_calls, tool_results):
                yield _sse({"type": "tool_end", "name": tc["name"], "output": result.content})

        reply = "".join(reply_parts).strip(
        ) or "I was unable to process your request."

        await _save_message(db, conversation_id, "user", message)
        job_ids = _extract_job_ids(reply)
        await _save_message(db, conversation_id, "assistant", reply, related_job_ids=job_ids)

        yield _sse({"type": "done", "conversation_id": str(conversation_id), "job_ids": job_ids})

    except Exception as e:
        logger.exception("Stream agent error: %s", e)
        yield _sse({"type": "error", "message": str(e)})

    finally:
        _db_ctx.reset(db_token)
        _redis_ctx.reset(redis_token)
        _conv_id_ctx.reset(conv_token)
