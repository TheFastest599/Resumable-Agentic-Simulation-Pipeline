from fastapi import APIRouter

from tasks.registry import TASK_METADATA

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("")
async def list_tasks():
    """Return all registered simulation tasks with descriptions and default payloads."""
    return {
        "tasks": [
            {"name": name, "description": meta["description"], "default_payload": meta["default_payload"]}
            for name, meta in TASK_METADATA.items()
        ],
        "total": len(TASK_METADATA),
    }
