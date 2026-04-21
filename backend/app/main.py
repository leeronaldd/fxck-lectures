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
from fastapi.responses import FileResponse, StreamingResponse

from app.auth import get_current_user
from app.models import UploadResponse

# ─── Sentry (optional) ──────────────────────────────────────────────────────
# Initialize before app = FastAPI() so the ASGI integration wraps routes. No-op
# if SENTRY_DSN is unset, so the service runs identically until you create a
# Sentry project and drop the DSN into Cloud Run env vars.
_sentry_dsn = os.environ.get("SENTRY_DSN", "")
if _sentry_dsn:
    import sentry_sdk
    sentry_sdk.init(
        dsn=_sentry_dsn,
        # 10% trace sampling is plenty for trend-spotting without burning
        # through the free 5k events/month tier once you grow.
        traces_sample_rate=0.1,
        # Don't send PII by default — our users upload lecture content which
        # may include personal names in slides.
        send_default_pii=False,
        environment=os.environ.get("SENTRY_ENV", "production"),
    )

app = FastAPI(title="Fxck Lectures API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://fxck-lectures.vercel.app",
        "https://klareai.com",
        "https://www.klareai.com",
    ],
    allow_origin_regex=r"https://fxck-lectures-.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Temp directory for uploads
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", Path(__file__).parent.parent / "data" / "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Hard cap per uploaded file. A 2-hour lecture video at 720p is roughly
# 300-400 MB; 500 MB leaves headroom for higher bitrates. Prevents a single
# upload from filling the instance's 2 Gi memory or running up GCS costs.
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", str(500 * 1024 * 1024)))

# Map file_id → original filename (in-memory, lost on restart — acceptable)
_original_filenames: dict[str, str] = {}

# Supabase config
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://husdhmaijvughqezlmjt.supabase.co")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "sb_publishable_CwLFt3Pfeaeq5iP0foroCA_tMmPucAy")
# Service role key bypasses RLS — used for background saves where user JWT may have expired
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# Stripe config
import stripe
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

# Pro tier: existing prices (already live in Stripe)
STRIPE_PRICE_MONTHLY = os.environ.get(
    "STRIPE_PRICE_PRO_MONTHLY", "price_1TKSLDGW2ryevu4Tytl0EGlA"
)
STRIPE_PRICE_YEARLY = os.environ.get(
    "STRIPE_PRICE_PRO_YEARLY", "price_1TKSLDGW2ryevu4TtsoJE3Am"
)
# Max tier: created later in Stripe — set IDs via env vars after creation.
# Empty string is fine if Max isn't live yet (checkout for Max would fail
# with a clear "price not configured" error).
STRIPE_PRICE_MAX_MONTHLY = os.environ.get("STRIPE_PRICE_MAX_MONTHLY", "")
STRIPE_PRICE_MAX_YEARLY = os.environ.get("STRIPE_PRICE_MAX_YEARLY", "")

FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://klareai.com")

# Unlimited usage for these emails (store canonical form — lowercase, no dots for gmail)
UNLIMITED_EMAILS = {
    "leewanghong0215@gmail.com",
    "leepakwai0706@gmail.com",
}
FREE_USAGE_LIMIT = 2
# Stripe statuses that grant paid access. "trialing" included so free trials
# (if you ever add them) work; everything else (past_due, canceled, unpaid,
# incomplete) falls back to the free lifetime cap.
PAID_STATUSES = {"active", "trialing"}

# ─── Tier config ────────────────────────────────────────────────────────────
# Each tier = (period limit, daily cap). Daily cap prevents one user from
# burning the entire monthly allowance in a single hour at scale.
# Tier name is stored in user_profiles.subscription_tier by the webhook.
TIER_LIMITS: dict[str, dict[str, int]] = {
    "pro": {"period_limit": 15, "daily_cap": 5},
    "max": {"period_limit": 50, "daily_cap": 10},
}

# Reverse map: Stripe price_id → tier name. Webhook reads price from
# subscription.items[0].price.id and looks up the tier here. Empty price
# IDs (Max not yet live) are excluded so they don't shadow real lookups.
PRICE_TO_TIER: dict[str, str] = {}
for _pid in (STRIPE_PRICE_MONTHLY, STRIPE_PRICE_YEARLY):
    if _pid:
        PRICE_TO_TIER[_pid] = "pro"
for _pid in (STRIPE_PRICE_MAX_MONTHLY, STRIPE_PRICE_MAX_YEARLY):
    if _pid:
        PRICE_TO_TIER[_pid] = "max"

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


def _service_headers(extra: dict | None = None) -> dict:
    """Build Supabase auth headers for a service-role call.

    With the new `sb_secret_` key format, service-role access is granted by
    sending the key as the `apikey` header alone. The legacy pattern of
    sending it as `Authorization: Bearer <key>` fails because PostgREST
    tries to decode the Bearer token as a JWT, and the new format isn't
    one ("Expected 3 parts in JWT; got 1" on 401).

    Also works with legacy JWT service_role keys (Supabase accepts JWT
    tokens via the apikey header too), so this is format-agnostic.

    Falls back to anon headers if SUPABASE_SERVICE_KEY isn't configured —
    caller will hit RLS and fail explicitly instead of silently using a
    wrong-format bearer.
    """
    headers = {"apikey": SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY}
    if extra:
        headers.update(extra)
    return headers


def _user_headers(user_token: str, extra: dict | None = None) -> dict:
    """Build Supabase auth headers for a user-scoped call (RLS enforced).

    apikey = anon key (identifies project + grants anon role), Authorization
    = user's JWT (identifies the user so RLS policies can filter by uid).
    """
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {user_token}",
    }
    if extra:
        headers.update(extra)
    return headers


async def _get_subscription(token: str, user_id: str) -> dict | None:
    """Fetch the user's subscription row from user_profiles. Returns None on
    any error (treat as free tier — fail-safe default, never accidentally
    grants paid access).
    """
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/user_profiles",
                params={
                    "user_id": f"eq.{user_id}",
                    "select": (
                        "subscription_status,"
                        "subscription_tier,"
                        "subscription_period_start,"
                        "subscription_period_end"
                    ),
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
    except Exception as e:
        print(f"  [usage] subscription fetch failed: {e}")
    return None


async def _reserve_usage_slot(user: dict, request: Request) -> str | None:
    """Atomically reserve a usage slot for this user. Returns the usage row ID
    on success, raises 403 if the user is over limit.

    Tier logic:
      • Unlimited whitelist emails → sentinel "unlimited", skip RPC.
      • Paid (status in PAID_STATUSES) with a known tier → tier-specific
        period_limit + daily_cap. Window anchored to subscription_period_start.
      • Paid but missing period_start (webhook lag) → fall back to free tier
        cap; webhook will catch up and unlock them once it fires.
      • Everyone else → FREE_USAGE_LIMIT lifetime.

    Uses the `try_record_usage` Postgres RPC (window+daily version in
    migrations/2026-04-16-daily-cap-and-tiers.sql). Callers must call
    `_refund_usage_slot(usage_id)` if the pipeline later fails.
    """
    email = _normalize_email(user.get("email", ""))
    if email in UNLIMITED_EMAILS:
        return "unlimited"

    user_id = user["id"]
    token = request.headers.get("authorization", "").split(" ", 1)[-1]

    sub = await _get_subscription(token, user_id)
    period_start: str | None = None
    daily_cap: int | None = None
    tier_name: str | None = None

    is_paid = (
        sub
        and sub.get("subscription_status") in PAID_STATUSES
        and sub.get("subscription_period_start")
    )
    if is_paid:
        tier_name = sub.get("subscription_tier") or "pro"  # default to pro if tier wasn't recorded
        tier = TIER_LIMITS.get(tier_name, TIER_LIMITS["pro"])
        limit = tier["period_limit"]
        daily_cap = tier["daily_cap"]
        period_start = sub["subscription_period_start"]
    else:
        limit = CUSTOM_LIMITS.get(email, FREE_USAGE_LIMIT)

    rpc_body: dict = {
        "p_user_id": user_id,
        "p_email": user.get("email", ""),
        "p_limit": limit,
    }
    if period_start:
        rpc_body["p_period_start"] = period_start
    if daily_cap is not None:
        rpc_body["p_daily_cap"] = daily_cap

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/rpc/try_record_usage",
            json=rpc_body,
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        if resp.status_code != 200:
            print(f"  [usage] RPC failed {resp.status_code}: {resp.text[:200]}")
            raise HTTPException(
                status_code=503,
                detail="Usage tracking unavailable. Please try again in a moment.",
            )

        result = resp.json()
        if result is None:
            # RPC returns NULL for either the period limit or the daily cap.
            # Message is paid-tier-specific so the user knows what to do.
            if is_paid:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        f"You've hit your {tier_name.title() if tier_name else 'plan'} "
                        f"limit for this billing period or your daily {daily_cap}-run "
                        f"cap. Try again tomorrow or upgrade for more."
                    ),
                )
            raise HTTPException(
                status_code=403,
                detail=f"You've used all {limit} of your lectures. Upgrade for unlimited access.",
            )
        return str(result)


async def _refund_usage_slot(token: str, usage_id: str) -> None:
    """Delete a reserved usage row after a pipeline failure. Best-effort —
    logs and swallows on failure. Safe no-op for the 'unlimited' sentinel.
    """
    if not usage_id or usage_id == "unlimited":
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{SUPABASE_URL}/rest/v1/rpc/refund_usage",
                json={"p_usage_id": usage_id},
                headers={
                    "apikey": SUPABASE_ANON_KEY,
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code not in (200, 204):
                print(f"  [usage] refund RPC failed {resp.status_code}: {resp.text[:200]}")
            else:
                print(f"  [usage] refunded slot {usage_id}")
    except Exception as e:
        print(f"  [usage] refund raised: {e}")


async def _update_session_status(
    token: str,
    user_id: str,
    session_id: str,
    status: str,
    error_message: str | None = None,
) -> None:
    """Flip a session row's status (processing | ready | failed) without touching content.

    Best-effort: logs and swallows on failure so it never masks the underlying
    pipeline exception. The frontend reads `status` to decide whether to show
    a spinner, an error+retry, or the markdown.
    """
    payload: dict = {"status": status}
    if error_message is not None:
        payload["error_message"] = error_message[:500]  # cap so it fits in a TEXT column comfortably
    # Prefer service headers (bypass RLS) so long-running pipelines can still
    # flip status after the user JWT expires. Fall back to user headers if
    # service key isn't configured.
    headers = _service_headers({
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }) if SUPABASE_SERVICE_KEY else _user_headers(token, {
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    })
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.patch(
                f"{SUPABASE_URL}/rest/v1/sessions",
                params={"id": f"eq.{session_id}", "user_id": f"eq.{user_id}"},
                json=payload,
                headers=headers,
            )
            if resp.status_code not in (200, 204):
                print(f"  [status] PATCH {status} failed {resp.status_code}: {resp.text[:200]}")
            else:
                print(f"  [status] session={session_id} → {status}"
                      + (f" ({error_message[:80]}...)" if error_message else ""))
    except Exception as e:
        print(f"  [status] PATCH {status} raised: {e}")


async def _save_session_partial(
    user_id: str,
    session_id: str,
    slides: list,
    transcript: list,
) -> None:
    """Persist streamed sections as a partial snapshot without flipping status.

    Runs periodically during generation so cross-device viewers can see what's
    been produced, and so a Cloud Run scale-down mid-pipeline doesn't wipe out
    work the client already received over SSE. Status stays 'processing' — the
    final _save_session_direct call flips it to 'ready' once generation ends.
    """
    if not SUPABASE_SERVICE_KEY:
        return  # partial saves require service key to bypass RLS reliably
    if not slides and not transcript:
        return
    markdown = json.dumps(
        {"slides": slides, "transcript": transcript}, ensure_ascii=False,
    )
    headers = _service_headers({
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    })
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.patch(
                f"{SUPABASE_URL}/rest/v1/sessions",
                params={"id": f"eq.{session_id}", "user_id": f"eq.{user_id}"},
                json={"markdown": markdown},
                headers=headers,
            )
            if resp.status_code not in (200, 204):
                print(f"  [partial] PATCH failed {resp.status_code}: {resp.text[:200]}")
            else:
                print(f"  [partial] session={session_id} sections={len(transcript)} bytes={len(markdown)}")
    except Exception as e:
        print(f"  [partial] PATCH raised: {e}")


async def _save_session_direct(token: str, user_id: str, name: str, output: dict, session_id: str | None = None) -> str:
    """Save pipeline output to Supabase using a pre-captured auth token.

    Used by background pipeline worker where the request object may be stale.
    Also flips status → 'ready' so the frontend reader unblocks.

    Falls back to service role key if the user JWT has expired (common when
    pipeline runs take >10 min due to cold starts).
    """
    # Prefer service key for background saves — user JWT may have expired
    # during long pipeline runs. Service key bypasses RLS via apikey header
    # (not Authorization Bearer — the new sb_secret_ format isn't a JWT).
    if SUPABASE_SERVICE_KEY:
        print(f"  [save] Using service role key (user JWT may be expired)")
        auth_for_patch = _service_headers({
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        })
        auth_for_post = _service_headers({
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        })
    else:
        auth_for_patch = _user_headers(token, {
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        })
        auth_for_post = _user_headers(token, {
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        })

    markdown_len = len(output.get("markdown", ""))
    async with httpx.AsyncClient() as client:
        if session_id:
            resp = await client.patch(
                f"{SUPABASE_URL}/rest/v1/sessions",
                params={"id": f"eq.{session_id}", "user_id": f"eq.{user_id}"},
                json={
                    "name": name,
                    "markdown": output.get("markdown", ""),
                    "concept_groups": output.get("concept_groups", []),
                    "verification_report": output.get("verification_report", []),
                    "status": "ready",
                    "error_message": None,
                },
                headers=auth_for_patch,
            )
            if resp.status_code not in (200, 204):
                print(f"  [save] PATCH failed {resp.status_code}: {resp.text[:300]}")
                raise RuntimeError(
                    f"Supabase PATCH failed: {resp.status_code} {resp.text[:200]}"
                )
            rows = resp.json() if resp.text else []
            if isinstance(rows, list) and len(rows) == 0:
                print(f"  [save] PATCH matched 0 rows for session {session_id} "
                      f"(user {user_id}) — likely RLS or missing row. "
                      f"Falling back to POST-create.")
                # RLS blocked update or row doesn't exist — create it under this user
                resp2 = await client.post(
                    f"{SUPABASE_URL}/rest/v1/sessions",
                    json={
                        "id": session_id,
                        "user_id": user_id,
                        "name": name,
                        "markdown": output.get("markdown", ""),
                        "concept_groups": output.get("concept_groups", []),
                        "verification_report": output.get("verification_report", []),
                        "status": "ready",
                    },
                    headers=auth_for_post,
                )
                if resp2.status_code not in (200, 201, 204):
                    print(f"  [save] Fallback POST failed {resp2.status_code}: {resp2.text[:300]}")
                    raise RuntimeError(
                        f"Supabase POST fallback failed: {resp2.status_code} {resp2.text[:200]}"
                    )
            print(f"  [save] PATCH session={session_id} markdown_len={markdown_len}")
        else:
            session_id = str(uuid.uuid4())
            resp = await client.post(
                f"{SUPABASE_URL}/rest/v1/sessions",
                json={
                    "id": session_id,
                    "user_id": user_id,
                    "name": name,
                    "markdown": output.get("markdown", ""),
                    "concept_groups": output.get("concept_groups", []),
                    "verification_report": output.get("verification_report", []),
                    "status": "ready",
                },
                headers=auth_for_post,
            )
            if resp.status_code not in (200, 201, 204):
                print(f"  [save] POST failed {resp.status_code}: {resp.text[:300]}")
                raise RuntimeError(
                    f"Supabase POST failed: {resp.status_code} {resp.text[:200]}"
                )
            print(f"  [save] POST session={session_id} markdown_len={markdown_len}")
    return session_id


async def _save_session(user: dict, request: Request, name: str, output: dict, session_id: str | None = None) -> str:
    """Save pipeline output as a session in Supabase. Updates existing session if session_id provided, otherwise creates new. Returns session ID."""
    token = request.headers.get("authorization", "").split(" ", 1)[-1]
    async with httpx.AsyncClient() as client:
        if session_id:
            # Update existing session with pipeline output
            await client.patch(
                f"{SUPABASE_URL}/rest/v1/sessions",
                params={
                    "id": f"eq.{session_id}",
                    "user_id": f"eq.{user['id']}",
                },
                json={
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
        else:
            # Create new session (backward compat)
            session_id = str(uuid.uuid4())
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


# Serve screenshot images from data/output/screenshots/
SCREENSHOTS_DIR = Path(__file__).parent.parent / "data" / "output" / "screenshots"


@app.get("/api/screenshots/{filename}")
async def get_screenshot(filename: str):
    """Serve extracted lecture slide images."""
    # Sanitize filename to prevent path traversal
    safe_name = Path(filename).name
    file_path = SCREENSHOTS_DIR / safe_name
    if not file_path.exists():
        raise HTTPException(404, "Screenshot not found")
    mime = "image/png" if safe_name.endswith(".png") else "image/jpeg"
    return FileResponse(file_path, media_type=mime)


def _save_upload_bounded(upload: UploadFile, dst_path: Path) -> int:
    """Stream-copy an uploaded file to disk, bailing out past MAX_UPLOAD_BYTES.

    Returns bytes written on success. Raises HTTPException(413) on overflow
    and deletes any partial file so oversize uploads can't fill the instance
    disk one chunk at a time.
    """
    total = 0
    try:
        with open(dst_path, "wb") as f:
            while True:
                chunk = upload.file.read(1024 * 1024)  # 1 MB chunks
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    f.close()
                    dst_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            f"File too large. Maximum is "
                            f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
                        ),
                    )
                f.write(chunk)
    except HTTPException:
        raise
    except Exception:
        dst_path.unlink(missing_ok=True)
        raise
    return total


@app.post("/api/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Upload a transcript (.txt) or video (.mp4) file."""
    file_id = str(uuid.uuid4())
    ext = Path(file.filename or "file.txt").suffix
    file_path = UPLOAD_DIR / f"{file_id}{ext}"

    _save_upload_bounded(file, file_path)

    original = Path(file.filename or "file.txt").stem
    _original_filenames[file_id] = original

    return UploadResponse(file_id=file_id, filename=file.filename or "file.txt")


# Map file_id → slides paths for pipeline to pick up (supports multiple PDFs)
_slide_files: dict[str, list[Path]] = {}


@app.post("/api/upload-slides")
async def upload_slides(
    file: UploadFile = File(...),
    file_id: str = "",
    user: dict = Depends(get_current_user),
):
    """Upload lecture slides (PDF) to accompany a previously uploaded lecture.

    The file_id should match a previously uploaded transcript/video.
    Can be called multiple times for the same file_id to upload split
    slide decks (e.g. "Deformation processing 1.pdf" and "2.pdf").
    PDFs are merged in upload order before extraction.
    """
    if not file_id:
        raise HTTPException(400, "file_id is required — upload the lecture first")

    ext = Path(file.filename or "slides.pdf").suffix.lower()
    if ext not in (".pdf", ".pptx"):
        raise HTTPException(400, "Only PDF and PPTX slide files are supported")

    # Store with counter suffix so multiple uploads don't overwrite
    existing = _slide_files.get(file_id, [])
    idx = len(existing)
    slides_path = UPLOAD_DIR / f"{file_id}_slides_{idx}{ext}"
    _save_upload_bounded(file, slides_path)

    existing.append(slides_path)
    _slide_files[file_id] = existing

    return {"status": "ok", "slides_filename": file.filename, "file_id": file_id, "index": idx}


@app.post("/api/sessions")
async def create_session(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Create a new empty session (before upload/processing)."""
    body = await request.json()
    name = body.get("name", "New Lecture").strip()

    token = request.headers.get("authorization", "").split(" ", 1)[-1]
    session_id = str(uuid.uuid4())
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SUPABASE_URL}/rest/v1/sessions",
            json={
                "id": session_id,
                "user_id": user["id"],
                "name": name,
                "markdown": "",
                "concept_groups": [],
                "verification_report": [],
                "status": "pending",  # pipeline_worker flips → processing → ready/failed
            },
            headers={
                "apikey": SUPABASE_ANON_KEY,
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
        )
        if resp.status_code in (200, 201):
            data = resp.json()
            return data[0] if data else {"id": session_id, "name": name}
        raise HTTPException(status_code=resp.status_code, detail="Failed to create session")


@app.get("/api/sessions")
async def get_sessions(
    user: dict = Depends(get_current_user),
    request: Request = None,
):
    """Get user's saved sessions.

    Side-effect: before returning, any of this user's sessions that have
    been stuck in 'pending' or 'processing' for more than STUCK_SESSION_MIN
    minutes get auto-flipped to 'failed'. This heals runs where the Cloud
    Run instance died mid-pipeline (OOM, crash, scale-down) and left the
    session spinning forever. Runs on every sessions list load — cheap,
    self-healing, no cron needed.
    """
    import datetime as _dt

    token = request.headers.get("authorization", "").split(" ", 1)[-1]
    async with httpx.AsyncClient() as client:
        # Auto-heal stuck sessions for this user. ISO-8601 timestamp cutoff
        # so the comparison is server-side in Postgres (handles clock skew).
        stuck_cutoff_min = int(os.environ.get("STUCK_SESSION_MIN", "45"))
        cutoff = (
            _dt.datetime.now(_dt.timezone.utc)
            - _dt.timedelta(minutes=stuck_cutoff_min)
        ).isoformat()
        try:
            await client.patch(
                f"{SUPABASE_URL}/rest/v1/sessions",
                params={
                    "user_id": f"eq.{user['id']}",
                    "status": "in.(pending,processing)",
                    "created_at": f"lt.{cutoff}",
                },
                json={
                    "status": "failed",
                    "error_message": (
                        f"Processing timed out (no response for "
                        f"{stuck_cutoff_min}+ minutes). Please try again."
                    ),
                },
                headers={
                    "apikey": SUPABASE_ANON_KEY,
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
                timeout=5.0,
            )
        except Exception as e:
            # Never block the listing on a heal failure
            print(f"  [sessions] stuck-heal skipped: {e}")

        resp = await client.get(
            f"{SUPABASE_URL}/rest/v1/sessions",
            params={
                "user_id": f"eq.{user['id']}",
                "select": "id,name,created_at,status,error_message",
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
    }
    # Remove None values
    profile = {k: v for k, v in profile.items() if v is not None}

    async with httpx.AsyncClient() as client:
        # Check if profile exists
        check = await client.get(
            f"{SUPABASE_URL}/rest/v1/user_profiles",
            params={"user_id": f"eq.{user['id']}", "select": "id", "limit": "1"},
            headers={"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {token}"},
        )
        exists = check.status_code == 200 and check.json()

        if exists:
            # Update existing profile (user has UPDATE policy)
            resp = await client.patch(
                f"{SUPABASE_URL}/rest/v1/user_profiles",
                params={"user_id": f"eq.{user['id']}"},
                json=profile,
                headers={
                    "apikey": SUPABASE_ANON_KEY,
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation",
                },
            )
        else:
            # Insert new profile — use service role key to bypass RLS INSERT policy
            insert_headers = _service_headers({
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            }) if SUPABASE_SERVICE_KEY else _user_headers(token, {
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            })
            resp = await client.post(
                f"{SUPABASE_URL}/rest/v1/user_profiles",
                json=profile,
                headers=insert_headers,
            )

        if resp.status_code in (200, 201):
            data = resp.json()
            return data[0] if data else profile
        raise HTTPException(status_code=resp.status_code, detail=f"Failed to save profile: {resp.text}")


@app.post("/api/checkout")
async def create_checkout_session(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Create a Stripe Checkout session for upgrading.

    Body params:
      period: "monthly" | "yearly"  (default: yearly)
      tier:   "pro" | "max"          (default: pro)

    Backwards-compatible: existing frontend calls with only `period` get Pro.
    """
    body = await request.json()
    period = body.get("period", "yearly")
    tier = body.get("tier", "pro")

    # Pick the right price ID based on tier × period
    if tier == "max":
        price_id = STRIPE_PRICE_MAX_YEARLY if period == "yearly" else STRIPE_PRICE_MAX_MONTHLY
        if not price_id:
            raise HTTPException(
                status_code=503,
                detail="Max tier not yet configured. Please contact support.",
            )
    else:  # pro (default)
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
            # Belt-and-suspenders: both metadata and client_reference_id carry
            # the user_id so the webhook can link customer → user even if one
            # field gets stripped somewhere in the pipeline.
            metadata={"user_id": user["id"]},
            client_reference_id=user["id"],
            # Propagate user_id onto the subscription object too. Subscription
            # events (renewal, cancel) don't always include the Checkout
            # Session, so we need user_id reachable from the subscription.
            subscription_data={"metadata": {"user_id": user["id"]}},
        )
        return {"url": session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe error: {e}")


# ─── Stripe webhook ─────────────────────────────────────────────────────────

def _tier_from_subscription(sub: dict) -> str | None:
    """Pick the tier name ('pro' | 'max') by reading the first subscription
    item's price.id and looking it up in PRICE_TO_TIER. Returns None if the
    price isn't recognised — keeps the existing tier or defaults to 'pro'.
    """
    try:
        items = (sub.get("items") or {}).get("data") or []
        if items:
            price = items[0].get("price") or {}
            price_id = price.get("id")
            if price_id and price_id in PRICE_TO_TIER:
                return PRICE_TO_TIER[price_id]
    except Exception as e:
        print(f"  [stripe-webhook] tier lookup failed: {e}")
    return None


async def _upsert_subscription_by_user(
    user_id: str,
    *,
    stripe_customer_id: str | None = None,
    stripe_subscription_id: str | None = None,
    subscription_status: str | None = None,
    subscription_tier: str | None = None,
    period_start: str | None = None,
    period_end: str | None = None,
) -> None:
    """Write subscription fields to user_profiles using the service role key
    (webhooks are authenticated by Stripe signature, not Supabase JWT, so we
    must bypass RLS). Idempotent: if the profile row doesn't exist yet, we
    create a minimal one the quiz flow can fill in later.
    """
    if not SUPABASE_SERVICE_KEY:
        print("  [stripe-webhook] SUPABASE_SERVICE_KEY not set — cannot update subscription")
        return

    payload: dict = {}
    if stripe_customer_id is not None:
        payload["stripe_customer_id"] = stripe_customer_id
    if stripe_subscription_id is not None:
        payload["stripe_subscription_id"] = stripe_subscription_id
    if subscription_status is not None:
        payload["subscription_status"] = subscription_status
    if subscription_tier is not None:
        payload["subscription_tier"] = subscription_tier
    if period_start is not None:
        payload["subscription_period_start"] = period_start
    if period_end is not None:
        payload["subscription_period_end"] = period_end

    if not payload:
        return

    async with httpx.AsyncClient(timeout=10.0) as client:
        # Try PATCH first — zero-change if the row exists and fields match.
        resp = await client.patch(
            f"{SUPABASE_URL}/rest/v1/user_profiles",
            params={"user_id": f"eq.{user_id}"},
            json=payload,
            headers=_service_headers({
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            }),
        )
        if resp.status_code in (200, 204):
            rows = resp.json() if resp.text else []
            if isinstance(rows, list) and len(rows) > 0:
                print(f"  [stripe-webhook] updated profile user={user_id} "
                      f"status={subscription_status}")
                return
        # No row matched → create one. Covers the edge case where the user
        # checked out before completing the quiz flow.
        insert_payload = {"user_id": user_id, **payload}
        resp2 = await client.post(
            f"{SUPABASE_URL}/rest/v1/user_profiles",
            json=insert_payload,
            headers=_service_headers({
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            }),
        )
        if resp2.status_code not in (200, 201, 204):
            print(f"  [stripe-webhook] insert failed {resp2.status_code}: "
                  f"{resp2.text[:200]}")
        else:
            print(f"  [stripe-webhook] inserted profile user={user_id} "
                  f"status={subscription_status}")


async def _lookup_user_by_customer(stripe_customer_id: str) -> str | None:
    """Reverse lookup: stripe_customer_id → user_id. Used by subscription
    events that don't carry user metadata themselves.
    """
    if not SUPABASE_SERVICE_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                f"{SUPABASE_URL}/rest/v1/user_profiles",
                params={
                    "stripe_customer_id": f"eq.{stripe_customer_id}",
                    "select": "user_id",
                    "limit": "1",
                },
                headers=_service_headers(),
            )
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    return data[0].get("user_id")
    except Exception as e:
        print(f"  [stripe-webhook] customer lookup failed: {e}")
    return None


def _iso_from_stripe_ts(ts: int | None) -> str | None:
    """Convert a Stripe unix timestamp to an ISO-8601 string for Postgres."""
    if ts is None:
        return None
    import datetime as _dt
    return _dt.datetime.fromtimestamp(ts, tz=_dt.timezone.utc).isoformat()


@app.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe subscription lifecycle events.

    Signature-verified via STRIPE_WEBHOOK_SECRET. Any event without a valid
    signature is rejected with 400. Deliberately handles a narrow set of
    events — extra events we don't handle return 200 (so Stripe stops
    retrying) but are otherwise ignored.

    Idempotent: re-deliveries of the same event produce the same state in
    user_profiles (all operations are UPSERTs by user_id).
    """
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(500, "Webhook not configured (STRIPE_WEBHOOK_SECRET missing)")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        raise HTTPException(400, f"Invalid payload: {e}")
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(400, f"Invalid signature: {e}")

    event_type = event["type"]
    obj = event["data"]["object"]
    print(f"  [stripe-webhook] event={event_type} id={event.get('id')}")

    try:
        if event_type == "checkout.session.completed":
            # User finished paying. session.metadata carries user_id (set in
            # /api/checkout); session.customer + session.subscription are the
            # Stripe IDs we want to persist.
            user_id = (obj.get("metadata") or {}).get("user_id") \
                      or obj.get("client_reference_id")
            customer_id = obj.get("customer")
            subscription_id = obj.get("subscription")
            if not user_id:
                print("  [stripe-webhook] no user_id on checkout session — skipping")
                return {"received": True}

            # Fetch the subscription to get period dates + status + tier
            period_start = period_end = status = tier = None
            if subscription_id:
                try:
                    sub = stripe.Subscription.retrieve(subscription_id)
                    status = sub.get("status")
                    period_start = _iso_from_stripe_ts(sub.get("current_period_start"))
                    period_end = _iso_from_stripe_ts(sub.get("current_period_end"))
                    tier = _tier_from_subscription(sub)
                except Exception as e:
                    print(f"  [stripe-webhook] subscription fetch failed: {e}")

            await _upsert_subscription_by_user(
                user_id,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                subscription_status=status or "active",
                subscription_tier=tier,
                period_start=period_start,
                period_end=period_end,
            )

        elif event_type == "customer.subscription.updated":
            # Fired on renewal (period advances), status change (past_due,
            # active), or cancel-at-period-end flag flips. Locate the user
            # via metadata first (set via subscription_data on checkout),
            # then fall back to stripe_customer_id lookup.
            user_id = (obj.get("metadata") or {}).get("user_id")
            customer_id = obj.get("customer")
            if not user_id and customer_id:
                user_id = await _lookup_user_by_customer(customer_id)
            if not user_id:
                print("  [stripe-webhook] subscription.updated: no user found — skipping")
                return {"received": True}

            # subscription.updated carries the full subscription object
            # including items[].price.id, so we can detect tier changes
            # (e.g. user upgraded Pro → Max).
            await _upsert_subscription_by_user(
                user_id,
                stripe_customer_id=customer_id,
                stripe_subscription_id=obj.get("id"),
                subscription_status=obj.get("status"),
                subscription_tier=_tier_from_subscription(obj),
                period_start=_iso_from_stripe_ts(obj.get("current_period_start")),
                period_end=_iso_from_stripe_ts(obj.get("current_period_end")),
            )

        elif event_type == "customer.subscription.deleted":
            # Subscription terminated (either immediate cancel or period-end
            # cancel firing). Flip status to 'canceled' so the user drops
            # back to free-tier limits on the next reserve attempt.
            user_id = (obj.get("metadata") or {}).get("user_id")
            customer_id = obj.get("customer")
            if not user_id and customer_id:
                user_id = await _lookup_user_by_customer(customer_id)
            if not user_id:
                print("  [stripe-webhook] subscription.deleted: no user found — skipping")
                return {"received": True}

            await _upsert_subscription_by_user(
                user_id,
                subscription_status="canceled",
            )

        elif event_type == "invoice.payment_failed":
            # Renewal charge failed — typically expired card or insufficient
            # funds. Stripe will auto-retry per Smart Retries (3 attempts
            # over ~3 weeks). During that window, subscription.status moves
            # active → past_due, which subscription.updated already
            # propagates to user_profiles. PAID_STATUSES excludes past_due,
            # so the user falls back to free limits on next reserve.
            #
            # We additionally log the failure so we can spot churn patterns
            # in Cloud Run logs without standing up Stripe Sigma queries.
            customer_id = obj.get("customer")
            sub_id = obj.get("subscription")
            attempt = obj.get("attempt_count")
            next_attempt = obj.get("next_payment_attempt")
            print(
                f"  [stripe-webhook] payment_failed customer={customer_id} "
                f"sub={sub_id} attempt={attempt} next_retry_ts={next_attempt}"
            )
            # No state mutation here — subscription.updated handles the
            # active → past_due transition idempotently. Touching state
            # twice would just race with that handler.

        else:
            # Unhandled event type — return 200 so Stripe doesn't retry.
            pass

    except Exception as e:
        # Never 500 to Stripe on handler error — they'll retry relentlessly
        # and our logs fill up. Log and acknowledge.
        print(f"  [stripe-webhook] handler error on {event_type}: {e}")

    return {"received": True}


@app.get("/api/run/{file_id}")
async def run_pipeline_stream(
    file_id: str,
    session_id: str | None = None,
    user: dict = Depends(get_current_user),
    request: Request = None,
):
    """Run the pipeline and stream progress via SSE."""
    # Atomically reserve a usage slot before running. Closes two loopholes:
    #   (a) Parallel clicks can no longer bypass the limit — the RPC serializes
    #       per user_id via pg_advisory_xact_lock.
    #   (b) A tab-close mid-run no longer leaves the counter uncharged — the
    #       slot is taken now, and only REFUNDED if the pipeline fails.
    # Sentinel "unlimited" is returned for whitelisted emails (no refund path).
    usage_id = await _reserve_usage_slot(user, request)

    matching = list(UPLOAD_DIR.glob(f"{file_id}.*"))
    if not matching:
        # File vanished — refund the slot we just reserved
        await _refund_usage_slot(
            request.headers.get("authorization", "").split(" ", 1)[-1],
            usage_id,
        )
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
    cancel_event = threading.Event()

    # Capture auth token NOW — request object may be stale after SSE disconnects
    auth_token = request.headers.get("authorization", "").split(" ", 1)[-1]

    # Check if slides were uploaded for this file.
    # First check in-memory list (same instance), then check disk
    # (handles the case where upload-slides and run hit different
    # Cloud Run instances — the in-memory dict is per-instance).
    slides_paths: list[Path] = _slide_files.get(file_id, [])
    if not slides_paths:
        # Scan disk for slides files (numbered: _slides_0.pdf, _slides_1.pdf, ...)
        for i in range(20):  # max 20 slide files
            for ext in (".pdf", ".pptx"):
                candidate = UPLOAD_DIR / f"{file_id}_slides_{i}{ext}"
                if candidate.exists():
                    slides_paths.append(candidate)
        # Also check legacy single-file naming
        if not slides_paths:
            for ext in (".pdf", ".pptx"):
                candidate = UPLOAD_DIR / f"{file_id}_slides{ext}"
                if candidate.exists():
                    slides_paths.append(candidate)
        if slides_paths:
            print(f"  [run] Found {len(slides_paths)} slides file(s) on disk")

    # Merge multiple PDFs into one if needed
    slides_path: Path | None = None
    if len(slides_paths) == 1:
        slides_path = slides_paths[0]
    elif len(slides_paths) > 1:
        try:
            import fitz
            merged = fitz.open()
            for sp in slides_paths:
                doc = fitz.open(str(sp))
                merged.insert_pdf(doc)
                doc.close()
            merged_path = UPLOAD_DIR / f"{file_id}_slides_merged.pdf"
            merged.save(str(merged_path))
            merged.close()
            slides_path = merged_path
            print(f"  [run] Merged {len(slides_paths)} PDFs → {merged_path} ({merged_path.stat().st_size // 1024} KB)")
        except Exception as e:
            print(f"  [run] PDF merge failed, using first file: {e}")
            slides_path = slides_paths[0]

    def pipeline_worker():
        nonlocal finished
        from app.pipeline import run_pipeline

        import asyncio as _asyncio

        def _run_async(coro):
            """Run an async coroutine from this sync thread without leaking loops."""
            loop = _asyncio.new_event_loop()
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

        # Flip session → 'processing' so frontend reader can show a spinner
        # instead of "No lecture loaded" if the user navigates there mid-run.
        if session_id:
            try:
                _run_async(_update_session_status(auth_token, user["id"], session_id, "processing"))
            except Exception as e:
                print(f"  [worker] failed to set processing status: {e}")

        last_progress = None
        pipeline_error: Exception | None = None
        # Accumulate streamed sections so a partial snapshot can be written to
        # Supabase as generation progresses. Without this, only the final
        # 'done' event triggers a save — so a crash or Cloud Run scale-down
        # mid-run leaves the session row empty even though the client
        # received the content over SSE.
        partial_slides: list = []
        partial_transcript: list = []
        PARTIAL_SAVE_EVERY = 3
        try:
            for progress in run_pipeline(input_path, user_profile=user_profile,
                                         slides_path=str(slides_path) if slides_path else None,
                                         cancel_event=None):  # Never cancel — always finish
                with lock:
                    events.append(progress)
                last_progress = progress

                # Accumulate section payloads for progressive persistence
                section = progress.get("section")
                if section and session_id:
                    slide = section.get("slide")
                    tx = section.get("transcript")
                    if slide:
                        partial_slides.append(slide)
                    if tx:
                        partial_transcript.append(tx)
                    if len(partial_transcript) % PARTIAL_SAVE_EVERY == 0:
                        try:
                            _run_async(_save_session_partial(
                                user["id"], session_id,
                                list(partial_slides), list(partial_transcript),
                            ))
                        except Exception as e:
                            print(f"  [worker] partial save raised: {e}")

                # Pipeline reported its own structured error — capture and stop
                if progress.get("status") == "error":
                    pipeline_error = RuntimeError(progress.get("error") or "pipeline reported error")
                    break
        except Exception as e:
            pipeline_error = e
            print(f"  [worker] pipeline raised: {e}")
            with lock:
                events.append({"status": "error", "stage": "pipeline", "progress": 0,
                                "error": "Something went wrong processing your lecture. Your run has been refunded — please try again."})

        # Save session even if client disconnected (result persists in Supabase)
        if (
            last_progress
            and last_progress.get("status") == "done"
            and last_progress.get("output")
            and pipeline_error is None
        ):
            try:
                session_name = original_filename.replace("-", " ").replace("_", " ").title()
                _run_async(_save_session_direct(
                    auth_token, user["id"], session_name,
                    last_progress["output"], session_id=session_id
                ))
                print(f"  Session saved for {file_id} (background)")
            except Exception as e:
                print(f"  Background session save failed: {e}")
                pipeline_error = e  # surface the save failure as a pipeline failure

        # On any failure (pipeline crash OR save crash), flush the last
        # accumulated snapshot so the user doesn't lose content that already
        # streamed to the client. Then mark status so the frontend reader
        # shows either a readable lecture (partial) or a retry button (empty).
        if pipeline_error is not None and session_id:
            has_partial = bool(partial_transcript)
            if has_partial:
                try:
                    _run_async(_save_session_partial(
                        user["id"], session_id,
                        list(partial_slides), list(partial_transcript),
                    ))
                except Exception as e:
                    print(f"  [worker] final partial save raised: {e}")
            try:
                _run_async(_update_session_status(
                    auth_token, user["id"], session_id,
                    "ready" if has_partial else "failed",
                    error_message=None if has_partial else str(pipeline_error),
                ))
            except Exception as e:
                print(f"  [worker] failed to set final status: {e}")

        # Refund the usage slot we reserved up-front if the pipeline failed.
        # On success we leave the slot taken — that's how the 2-lifetime cap
        # holds even when the client disconnected before the 'done' event.
        if pipeline_error is not None:
            try:
                _run_async(_refund_usage_slot(auth_token, usage_id))
            except Exception as e:
                print(f"  [worker] refund raised: {e}")

        with lock:
            finished = True

    # Start pipeline in background thread (NOT daemon — survives SSE disconnect)
    thread = threading.Thread(target=pipeline_worker, daemon=False)
    thread.start()

    async def event_stream():
        sent = 0
        try:
            while True:
                # Check if client disconnected — DON'T cancel the pipeline.
                # Let it finish in the background so the result gets saved
                # to the user's session. They can reload and find it there.
                if await request.is_disconnected():
                    print(f"  Client disconnected — pipeline continues in background for {file_id}")
                    return

                with lock:
                    new_events = events[sent:]
                    is_finished = finished

                for progress in new_events:
                    payload = {
                        "status": progress.get("status", "running"),
                        "current_stage": progress.get("stage"),
                        "progress": progress.get("progress", 0),
                        "error": progress.get("error"),
                        "output": progress.get("output"),
                    }
                    # Pass through streamed sections for progressive rendering
                    if "section" in progress:
                        payload["section"] = progress["section"]
                    data = json.dumps(payload)
                    yield f"data: {data}\n\n"
                    sent += 1

                    # On success, save session. Usage was already recorded at
                    # reservation time (see _reserve_usage_slot); we no longer
                    # record from the SSE path because tab-close-mid-run used
                    # to skip it entirely — now the slot stays taken unless
                    # the background worker explicitly refunds on failure.
                    if progress.get("status") == "done" and progress.get("output"):
                        try:
                            session_name = original_filename.replace("-", " ").replace("_", " ").title()
                            await _save_session(user, request, session_name, progress["output"], session_id=session_id)
                        except Exception:
                            pass  # Non-fatal — the worker thread also saves as backup

                    # Stop if done, error, or cancelled
                    if progress.get("status") in ("done", "error", "cancelled"):
                        return

                if is_finished:
                    return

                # Send keepalive comment every iteration to prevent Cloud Run timeout
                yield ": keepalive\n\n"
                await asyncio.sleep(2)
        except asyncio.CancelledError:
            # Don't cancel pipeline — let it finish and save the result
            print(f"  SSE stream cancelled — pipeline continues in background for {file_id}")

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
