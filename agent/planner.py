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

SYSTEM_PROMPT = """You are a scientific simulation assistant. Submit jobs, check status, aggregate results.

Tasks and their payload parameters (all keys are optional; use sensible defaults):
monte_carlo_pi(iterations:int)
option_pricing(S,K,T,r,sigma:float; simulations:int)
random_walk(steps,particles:int; dimensions:1|2|3)
monte_carlo_integration(samples:int; function:sin|cos|exp|x2|x3|sqrt; a,b:float)
heat_diffusion_1d(n_points,steps:int; diffusion_coeff:float)
heat_diffusion_2d(grid_size,steps:int; diffusion_coeff:float)
chemical_diffusion(grid_size,steps:int; diffusion_coeff:float)
population_spread(grid_size,steps:int; growth_rate:float)
matrix_multiply(size:int)
eigenvalue_decomp(size:int)
svd_decomposition(rows,cols:int)
pca_covariance(n_samples,n_features,n_components:int)
projectile_motion(initial_velocity,angle_deg,drag_coeff:float)
lotka_volterra(prey_initial,predator_initial:float; steps:int)
pendulum_motion(length,damping,initial_angle_deg:float; steps:int)
spring_mass(mass,spring_constant,damping:float; steps:int)
fluid_advection(n_particles,steps:int)
network_spread(n_nodes,steps:int; infection_prob,recovery_prob:float)
traffic_flow(road_length,n_vehicles,steps:int)
forest_fire(grid_size,steps:int; p_tree:float)
diffusion_reaction(grid_size,steps:int; f,k:float)
quantum_well(n_points:int; well_depth,well_width:float)
brownian_motion(n_particles,steps:int; diffusion_coeff:float; dimensions:1|2|3)
heat_conduction_varying(n_points,steps:int; conductivity_profile:step|linear|gaussian)
fractal_dla(grid_size,n_particles:int)
wave_propagation(grid_size,steps:int; wave_speed:float; dimensions:1|2)
population_genetics(population_size,generations,n_replicates:int; initial_allele_freq:float)
epidemic_sir(population,steps:int; beta,gamma:float; model:SIR|SEIR)
game_of_life(grid_size,steps:int; pattern:random|glider|blinker; initial_density:float)
financial_risk_mc(n_assets,n_scenarios,horizon_days:int; confidence:float)

Rules:
- Submit each job EXACTLY ONCE. Never re-submit.
- After submitting, tell the user the job_id and that it is queued.
- Do NOT call check_job_status after submitting. Jobs run in the background.
- Only call check_job_status when the user explicitly asks to check a job.
- If status is QUEUED or RUNNING, report it and tell the user to check back later.
- Never fabricate results.
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
        text = msg.content.get("text", "") if isinstance(msg.content, dict) else str(msg.content)
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

        messages: list[Any] = [SystemMessage(content=SYSTEM_PROMPT)] + history + [HumanMessage(content=message)]

        agent = get_agent()
        response = await agent.ainvoke({"messages": messages})

        ai_messages = [m for m in response["messages"] if isinstance(m, AIMessage)]
        raw = ai_messages[-1].content if ai_messages else ""
        reply = raw if isinstance(raw, str) else " ".join(p.get("text", "") for p in raw if isinstance(p, dict))
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

        messages: list[Any] = [SystemMessage(content=SYSTEM_PROMPT)] + history + [HumanMessage(content=message)]

        agent = get_agent()

        async for event in agent.astream_events({"messages": messages}, version="v2"):
            kind = event["event"]

            # LLM token chunks
            if kind == "on_chat_model_stream":
                chunk = event["data"].get("chunk")
                if chunk:
                    text = chunk.content if isinstance(chunk.content, str) else ""
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

        reply = "".join(reply_parts).strip() or "I was unable to process your request."

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
