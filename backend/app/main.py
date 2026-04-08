"""FastAPI backend for Fxck Lectures — wraps the Python pipeline as REST API."""

import json
import os
import shutil
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from app.auth import get_current_user
from app.models import UploadResponse

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
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", Path(__file__).parent.parent / "data" / "uploads"))
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


@app.get("/api/run/{file_id}")
async def run_pipeline_stream(
    file_id: str,
    user: dict = Depends(get_current_user),
):
    """Run the pipeline and stream progress via SSE.

    The pipeline runs synchronously inside this request — the SSE connection
    keeps Cloud Run alive for the entire duration (up to 900s timeout).
    """
    # Find the uploaded file
    matching = list(UPLOAD_DIR.glob(f"{file_id}.*"))
    if not matching:
        raise HTTPException(status_code=404, detail="File not found")

    input_path = str(matching[0])

    def event_stream():
        from app.pipeline import run_pipeline

        for progress in run_pipeline(input_path):
            data = json.dumps({
                "status": progress.get("status", "running"),
                "current_stage": progress.get("stage"),
                "progress": progress.get("progress", 0),
                "error": progress.get("error"),
                "output": progress.get("output"),
            })
            yield f"data: {data}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
