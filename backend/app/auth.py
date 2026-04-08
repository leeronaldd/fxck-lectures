"""Supabase JWT verification for FastAPI endpoints."""

import os

from fastapi import HTTPException, Request
from jose import jwt, JWTError

SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")


async def get_current_user(request: Request) -> dict:
    """Extract and verify Supabase JWT from Authorization header.

    Returns dict with 'id' and 'email' from the token payload.
    """
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = auth_header.split(" ", 1)[1]

    if not SUPABASE_JWT_SECRET:
        raise HTTPException(status_code=500, detail="JWT secret not configured")

    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return {
            "id": payload["sub"],
            "email": payload.get("email", ""),
        }
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
