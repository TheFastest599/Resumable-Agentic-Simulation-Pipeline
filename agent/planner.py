"""
LangGraph ReAct agent backed by Groq LLM.
Manages conversation memory in PostgreSQL.
"""
import logging
import uuid
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import redis.asyncio as aioredis

from agent.tools import ALL_TOOLS, _conv_id_ctx, _db_ctx, _redis_ctx
from core.config import settings
from models.conversation import Conversation
from models.message import Message

logger = logging.getLogger(__name__)

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
- Submit each job EXACTLY ONCE. Never re-submit a job you already submitted.
- After submitting, immediately tell the user the job_id and that it is queued/running.
- Do NOT call check_job_status after submitting — jobs run asynchronously in the background.
- Only call check_job_status when the user explicitly asks to check or poll a specific job.
- If check_job_status returns QUEUED or RUNNING, report the current status and tell the user to check back later. Do NOT submit the job again.
- Do not fabricate results.
"""

_llm = None


def _get_llm() -> ChatGroq:
    global _llm
    if _llm is None:
        _llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            groq_api_key=settings.GROQ_API_KEY,
            temperature=0.0,
        )
    return _llm


def _build_agent():
    return create_react_agent(_get_llm(), tools=ALL_TOOLS)


_agent = None


def get_agent():
    global _agent
    if _agent is None:
        _agent = _build_agent()
    return _agent


async def _load_history(db: AsyncSession, conversation_id: uuid.UUID, max_messages: int = 20) -> list:
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
    """Extract UUID-like strings from agent response."""
    import re
    return re.findall(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        text,
        re.IGNORECASE,
    )


async def run_agent_chat(
    message: str,
    conversation_id: uuid.UUID,
    db: AsyncSession,
    redis: aioredis.Redis,
) -> tuple[str, list[str]]:
    """
    Run the ReAct agent for one conversation turn.
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

        messages: list[Any] = [SystemMessage(
            content=SYSTEM_PROMPT)] + history + [HumanMessage(content=message)]

        agent = get_agent()
        response = await agent.ainvoke({"messages": messages})

        ai_messages = [m for m in response["messages"]
                       if isinstance(m, AIMessage)]
        raw = ai_messages[-1].content if ai_messages else ""
        reply = raw if isinstance(raw, str) else " ".join(
            p.get("text", "") for p in raw if isinstance(p, dict))
        reply = reply or "I was unable to process your request."

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
    Async generator that yields SSE-formatted lines for one conversation turn.

    Event types emitted:
      {"type": "token",      "content": "..."}          — LLM text chunk
      {"type": "tool_start", "name": "...", "input": {}} — tool invocation begins
      {"type": "tool_end",   "name": "...", "output": "..."} — tool result
      {"type": "done",       "conversation_id": "...", "job_ids": [...]} — final
      {"type": "error",      "message": "..."}           — on failure
    """
    import json as _json

    def _sse(payload: dict) -> str:
        return f"data: {_json.dumps(payload)}\n\n"

    db_token = _db_ctx.set(db)
    redis_token = _redis_ctx.set(redis)
    conv_token = _conv_id_ctx.set(conversation_id)

    reply_parts: list[str] = []

    try:
        await _ensure_conversation(db, conversation_id)
        history = await _load_history(db, conversation_id)

        if not history:
            conv = await db.get(Conversation, conversation_id)
            if conv and conv.name is None:
                conv.name = message[:20].strip()
                await db.commit()

        messages: list[Any] = [SystemMessage(
            content=SYSTEM_PROMPT)] + history + [HumanMessage(content=message)]

        agent = get_agent()

        async for event in agent.astream_events({"messages": messages}, version="v2"):
            kind = event["event"]

            # LLM token chunks
            if kind == "on_chat_model_stream":
                chunk = event["data"].get("chunk")
                if chunk:
                    text = chunk.content if isinstance(
                        chunk.content, str) else ""
                    if text:
                        reply_parts.append(text)
                        yield _sse({"type": "token", "content": text})

            # Tool call starts
            elif kind == "on_tool_start":
                yield _sse({
                    "type": "tool_start",
                    "name": event.get("name", ""),
                    "input": event["data"].get("input", {}),
                })

            # Tool call ends
            elif kind == "on_tool_end":
                output = event["data"].get("output", "")
                yield _sse({
                    "type": "tool_end",
                    "name": event.get("name", ""),
                    "output": output if isinstance(output, str) else _json.dumps(output),
                })

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
