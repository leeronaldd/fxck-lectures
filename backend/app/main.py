"""FastAPI backend for Fxck Lectures — wraps the Python pipeline as REST API."""

import asyncio
import json
import os
import shutil
import threading
import uuid
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, Request
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

# Map file_id → original filename (in-memory, lost on restart — acceptable)
_original_filenames: dict[str, str] = {}

# Supabase config
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://husdhmaijvughqezlmjt.supabase.co")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "sb_publishable_CwLFt3Pfeaeq5iP0foroCA_tMmPucAy")

# Stripe config
import stripe
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PRICE_MONTHLY = "price_1TKSLDGW2ryevu4Tytl0EGlA"
STRIPE_PRICE_YEARLY = "price_1TKSLDGW2ryevu4TtsoJE3Am"
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://fxck-lectures.vercel.app")

# Unlimited usage for these emails (store canonical form — lowercase, no dots for gmail)
UNLIMITED_EMAILS = {
    "leewanghong0215@gmail.com",
    "leepakwai0706@gmail.com",
}
FREE_USAGE_LIMIT = 2

# Custom limits per email (overrides FREE_USAGE_LIMIT)
# Store in canonical form (no dots for gmail). Add friends here:
CUSTOM_LIMITS = {
    # "friend@gmail.com": 10,
}


def _normalize_email(email: str) -> str:
    """Normalize email for consistent comparison.

    Gmail ignores dots in the local part and is case-insensitive:
    Lee.Wang.Hong0215@gmail.com = leewanghong0215@gmail.com
    Also handles googlemail.com (alias for gmail.com).
    """
    email = email.lower().strip()
    if not email or "@" not in email:
        return email

    local, domain = email.rsplit("@", 1)

    # Gmail/Googlemail: strip dots from local part
    if domain in ("gmail.com", "googlemail.com"):
        local = local.replace(".", "")
        domain = "gmail.com"  # normalize googlemail → gmail

    return f"{local}@{domain}"


async def _check_usage(user: dict, request: Request) -> None:
    """Check if user has remaining usage. Raises 403 if limit exceeded."""
    email = _normalize_email(user.get("email", ""))
    if email in UNLIMITED_EMAILS:
        return  # Unlimited access

    # Check custom limit or use default
    limit = CUSTOM_LIMITS.get(email, FREE_USAGE_LIMIT)

    user_id = user["id"]
    token = request.headers.get("authorization", "").split(" ", 1)[-1]

    # Query usage count from Supabase
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/usage",
            params={"user_id": f"eq.{user_id}", "select": "id"},
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {token}",
            },
        )
        if resp.status_code == 200:
            count = len(resp.json())
            if count >= limit:
                remaining = limit - count
                raise HTTPException(
                    status_code=403,
                    detail=f"You've used all {limit} of your lectures. Upgrade for unlimited access.",
                )


async def _record_usage(user: dict, request: Request) -> None:
    """Record a usage entry in Supabase."""
    token = request.headers.get("authorization", "").split(" ", 1)[-1]
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{SUPABASE_URL}/rest/v1/usage",
            json={"user_id": user["id"], "email": user.get("email", "")},
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
        )


async def _save_session(user: dict, request: Request, name: str, output: dict) -> str:
    """Save pipeline output as a session in Supabase. Returns session ID."""
    token = request.headers.get("authorization", "").split(" ", 1)[-1]
    session_id = str(uuid.uuid4())
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{SUPABASE_URL}/rest/v1/sessions",
            json={
                "id": session_id,
                "user_id": user["id"],
                "name": name,
                "markdown": output.get("markdown", ""),
                "concept_groups": output.get("concept_groups", []),
                "verification_report": output.get("verification_report", []),
            },
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
        )
    return session_id


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

    original = Path(file.filename or "file.txt").stem
    _original_filenames[file_id] = original

    return UploadResponse(file_id=file_id, filename=file.filename or "file.txt")


@app.get("/api/sessions")
async def get_sessions(
    user: dict = Depends(get_current_user),
    request: Request = None,
):
    """Get user's saved sessions."""
    token = request.headers.get("authorization", "").split(" ", 1)[-1]
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/sessions",
            params={
                "user_id": f"eq.{user['id']}",
                "select": "id,name,created_at",
                "order": "created_at.desc",
                "limit": "20",
            },
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {token}",
            },
        )
        if resp.status_code == 200:
            return resp.json()
        return []


@app.get("/api/sessions/{session_id}")
async def get_session(
    session_id: str,
    user: dict = Depends(get_current_user),
    request: Request = None,
):
    """Get a specific session's full data."""
    token = request.headers.get("authorization", "").split(" ", 1)[-1]
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/sessions",
            params={
                "id": f"eq.{session_id}",
                "user_id": f"eq.{user['id']}",
                "select": "*",
                "limit": "1",
            },
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {token}",
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return data[0]
        raise HTTPException(status_code=404, detail="Session not found")


@app.delete("/api/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user: dict = Depends(get_current_user),
    request: Request = None,
):
    """Delete a session owned by the current user."""
    token = request.headers.get("authorization", "").split(" ", 1)[-1]
    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{SUPABASE_URL}/rest/v1/sessions",
            params={
                "id": f"eq.{session_id}",
                "user_id": f"eq.{user['id']}",
            },
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {token}",
            },
        )
        if resp.status_code in (200, 204):
            return {"ok": True}
        raise HTTPException(status_code=resp.status_code, detail="Failed to delete session")


@app.post("/api/checkout")
async def create_checkout_session(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Create a Stripe Checkout session for upgrading to Pro."""
    body = await request.json()
    period = body.get("period", "yearly")
    price_id = STRIPE_PRICE_YEARLY if period == "yearly" else STRIPE_PRICE_MONTHLY

    email = user.get("email", "")

    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            customer_email=email,
            success_url=f"{FRONTEND_URL}/settings?tab=Billing&upgraded=true",
            cancel_url=f"{FRONTEND_URL}/settings?tab=Billing",
            metadata={"user_id": user["id"]},
        )
        return {"url": session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {e}")


@app.get("/api/run/{file_id}")
async def run_pipeline_stream(
    file_id: str,
    user: dict = Depends(get_current_user),
    request: Request = None,
):
    """Run the pipeline and stream progress via SSE."""
    # Check usage limits before running
    await _check_usage(user, request)

    matching = list(UPLOAD_DIR.glob(f"{file_id}.*"))
    if not matching:
        raise HTTPException(status_code=404, detail="File not found")

    input_path = str(matching[0])
    original_filename = _original_filenames.get(file_id, matching[0].stem)

    # Shared state between pipeline thread and async generator
    events: list[dict] = []
    finished = False
    lock = threading.Lock()

    def pipeline_worker():
        nonlocal finished
        from app.pipeline import run_pipeline

        for progress in run_pipeline(input_path):
            with lock:
                events.append(progress)
        with lock:
            finished = True

    # Start pipeline in background thread
    thread = threading.Thread(target=pipeline_worker, daemon=True)
    thread.start()

    async def event_stream():
        sent = 0
        while True:
            with lock:
                new_events = events[sent:]
                is_finished = finished

            for progress in new_events:
                data = json.dumps({
                    "status": progress.get("status", "running"),
                    "current_stage": progress.get("stage"),
                    "progress": progress.get("progress", 0),
                    "error": progress.get("error"),
                    "output": progress.get("output"),
                })
                yield f"data: {data}\n\n"
                sent += 1

                # On success, record usage and save session
                if progress.get("status") == "done" and progress.get("output"):
                    try:
                        await _record_usage(user, request)
                        session_name = original_filename.replace("-", " ").replace("_", " ").title()
                        await _save_session(user, request, session_name, progress["output"])
                    except Exception:
                        pass  # Non-fatal — don't fail the pipeline for tracking issues

                # Stop if done or error
                if progress.get("status") in ("done", "error"):
                    return

            if is_finished:
                return

            # Send keepalive comment every iteration to prevent Cloud Run timeout
            yield ": keepalive\n\n"
            await asyncio.sleep(5)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Alt-Svc": 'clear',
        },
    )
