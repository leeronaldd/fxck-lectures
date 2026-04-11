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
    allow_origin_regex=r"https://fxck-lectures-.*\.vercel\.app",
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


# Map file_id → slides path for pipeline to pick up
_slide_files: dict[str, Path] = {}


@app.post("/api/upload-slides")
async def upload_slides(
    file: UploadFile = File(...),
    file_id: str = "",
    user: dict = Depends(get_current_user),
):
    """Upload lecture slides (PDF) to accompany a previously uploaded lecture.

    The file_id should match a previously uploaded transcript/video.
    The pipeline will validate that slides match the transcript before
    running the expensive generation step.
    """
    if not file_id:
        raise HTTPException(400, "file_id is required — upload the lecture first")

    ext = Path(file.filename or "slides.pdf").suffix.lower()
    if ext not in (".pdf", ".pptx"):
        raise HTTPException(400, "Only PDF and PPTX slide files are supported")

    slides_path = UPLOAD_DIR / f"{file_id}_slides{ext}"
    with open(slides_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    _slide_files[file_id] = slides_path

    return {"status": "ok", "slides_filename": file.filename, "file_id": file_id}


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


@app.patch("/api/sessions/{session_id}")
async def rename_session(
    session_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Rename a session owned by the current user."""
    body = await request.json()
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Name is required")

    token = request.headers.get("authorization", "").split(" ", 1)[-1]
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{SUPABASE_URL}/rest/v1/sessions",
            params={
                "id": f"eq.{session_id}",
                "user_id": f"eq.{user['id']}",
            },
            json={"name": name},
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
        )
        if resp.status_code in (200, 204):
            return {"ok": True}
        raise HTTPException(status_code=resp.status_code, detail="Failed to rename session")


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


@app.get("/api/profile")
async def get_profile(
    user: dict = Depends(get_current_user),
    request: Request = None,
):
    """Get the current user's profile."""
    token = request.headers.get("authorization", "").split(" ", 1)[-1]
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/user_profiles",
            params={"user_id": f"eq.{user['id']}", "select": "*", "limit": "1"},
            headers={"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {token}"},
        )
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return data[0]
        return {}


@app.put("/api/profile")
async def update_profile(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Update or create the user's profile (upsert)."""
    body = await request.json()
    token = request.headers.get("authorization", "").split(" ", 1)[-1]

    # Build the profile data
    profile = {
        "user_id": user["id"],
        "display_name": body.get("display_name"),
        "avatar_color": body.get("avatar_color"),
        "study_program": body.get("study_program"),
        "study_year": body.get("study_year"),
        "frustration": body.get("frustration"),
        "referral_source": body.get("referral_source"),
        "updated_at": "now()",
    }
    # Remove None values
    profile = {k: v for k, v in profile.items() if v is not None}

    async with httpx.AsyncClient() as client:
        # Upsert — insert or update on conflict
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/user_profiles",
            json=profile,
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=representation",
            },
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            return data[0] if data else profile
        raise HTTPException(status_code=resp.status_code, detail="Failed to save profile")


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
            allow_promotion_codes=True,
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

    # Fetch user profile for personalized generation
    user_profile = None
    try:
        token = request.headers.get("authorization", "").split(" ", 1)[-1]
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/user_profiles",
                params={"user_id": f"eq.{user['id']}", "select": "study_program,study_year", "limit": "1"},
                headers={"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {token}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    user_profile = data[0]
    except Exception:
        pass  # Non-fatal — pipeline runs fine without profile

    # Shared state between pipeline thread and async generator
    events: list[dict] = []
    finished = False
    lock = threading.Lock()

    # Check if slides were uploaded for this file
    slides_path = _slide_files.get(file_id)

    def pipeline_worker():
        nonlocal finished
        from app.pipeline import run_pipeline

        for progress in run_pipeline(input_path, user_profile=user_profile,
                                     slides_path=str(slides_path) if slides_path else None):
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
