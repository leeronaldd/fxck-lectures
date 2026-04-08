"""FastAPI backend for Fxck Lectures — wraps the Python pipeline as REST API."""

import os
import shutil
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.auth import get_current_user
from app.models import (
    JobStatus,
    ProcessRequest,
    ProcessResponse,
    SessionOutput,
    SessionSummary,
    UploadResponse,
)
from app.pipeline import get_job, start_pipeline

app = FastAPI(title="Fxck Lectures API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://fxck-lectures.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Temp directory for uploads
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", Path(__file__).parent.parent.parent / "data" / "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Upload a transcript (.txt) or video (.mp4) file."""
    file_id = str(uuid.uuid4())
    ext = Path(file.filename or "file.txt").suffix
    file_path = UPLOAD_DIR / f"{file_id}{ext}"

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return UploadResponse(file_id=file_id, filename=file.filename or "file.txt")


@app.post("/api/process", response_model=ProcessResponse)
async def start_processing(
    req: ProcessRequest,
    user: dict = Depends(get_current_user),
):
    """Start the pipeline for an uploaded file. Returns job_id for status polling."""
    # Find the uploaded file
    matching = list(UPLOAD_DIR.glob(f"{req.file_id}.*"))
    if not matching:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="File not found")

    input_path = str(matching[0])
    job_id = start_pipeline(input_path, user["id"])

    # Session ID is the job ID for now (simplification)
    return ProcessResponse(job_id=job_id, session_id=job_id)


@app.get("/api/status/{job_id}", response_model=JobStatus)
async def get_status(
    job_id: str,
    user: dict = Depends(get_current_user),
):
    """Poll pipeline progress."""
    from fastapi import HTTPException

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not your job")

    return JobStatus(
        job_id=job_id,
        status=job["status"],
        current_stage=job.get("stage"),
        progress=job.get("progress", 0),
        error=job.get("error"),
    )


@app.get("/api/sessions", response_model=list[SessionSummary])
async def list_sessions(user: dict = Depends(get_current_user)):
    """List user's completed sessions.

    For MVP, scans in-memory jobs for completed ones.
    """
    from app.pipeline import jobs

    sessions = []
    for job_id, job in jobs.items():
        if job["user_id"] != user["id"]:
            continue
        if job["status"] != "done":
            continue
        sessions.append(
            SessionSummary(
                id=job_id,
                name=f"Session {job_id[:8]}",
                created_at="",
                status=job["status"],
                groups_count=len(job.get("output", {}).get("concept_groups", [])) if job.get("output") else 0,
            )
        )
    return sessions


@app.get("/api/sessions/{session_id}", response_model=SessionOutput)
async def get_session(
    session_id: str,
    user: dict = Depends(get_current_user),
):
    """Get session output (markdown, groups, verification)."""
    from fastapi import HTTPException
    from app.pipeline import jobs

    job = jobs.get(session_id)
    if not job:
        raise HTTPException(status_code=404, detail="Session not found")
    if job["user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not your session")
    if job["status"] != "done" or not job.get("output"):
        raise HTTPException(status_code=404, detail="Session output not ready")

    output = job["output"]
    return SessionOutput(
        id=session_id,
        name=f"Session {session_id[:8]}",
        markdown=output.get("markdown", ""),
        concept_groups=output.get("concept_groups"),
        verification_report=output.get("verification_report"),
    )
