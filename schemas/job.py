import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class JobSubmitRequest(BaseModel):
    task_name: str
    payload: dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=5, ge=1, le=10)
    max_retries: int = Field(default=3, ge=0)
    depends_on: list[uuid.UUID] = Field(default_factory=list)


class JobResponse(BaseModel):
    id: uuid.UUID
    task_name: str
    payload: dict[str, Any]
    status: str
    priority: int
    progress: float
    result: dict[str, Any] | None
    error: str | None
    retry_count: int
    max_retries: int
    worker_id: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int
