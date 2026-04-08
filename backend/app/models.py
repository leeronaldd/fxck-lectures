"""Pydantic models for API request/response schemas."""

from pydantic import BaseModel


class UploadResponse(BaseModel):
    file_id: str
    filename: str


class ProcessRequest(BaseModel):
    file_id: str
    name: str | None = None


class ProcessResponse(BaseModel):
    job_id: str
    session_id: str


class JobStatus(BaseModel):
    job_id: str
    status: str  # pending, running, done, error
    current_stage: str | None = None
    progress: int = 0
    error: str | None = None


class SessionSummary(BaseModel):
    id: str
    name: str
    created_at: str
    status: str
    groups_count: int


class SessionOutput(BaseModel):
    id: str
    name: str
    markdown: str
    concept_groups: list | None = None
    verification_report: list | None = None
