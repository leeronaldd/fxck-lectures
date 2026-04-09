"""Supabase JWT verification for FastAPI endpoints."""

import os

import httpx
from fastapi import HTTPException, Request
from jose import jwt, JWTError

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://husdhmaijvughqezlmjt.supabase.co")

# Cache the JWKS keys in memory
_jwks_cache: dict | None = None


async def _get_jwks() -> dict:
    """Fetch and cache Supabase JWKS public keys."""
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json")
        resp.raise_for_status()
        _jwks_cache = resp.json()
        return _jwks_cache


async def get_current_user(request: Request) -> dict:
    """Extract and verify Supabase JWT from Authorization header.

    Uses Supabase's JWKS endpoint for verification. Supports ES256, RS256, and HS256.
    """
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = auth_header.split(" ", 1)[1]

    # Use JWKS (supports ES256 and RS256)
    try:
        jwks = await _get_jwks()
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        alg = unverified_header.get("alg", "RS256")

        # Find matching key
        signing_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                signing_key = key
                break

        if not signing_key:
            raise HTTPException(status_code=401, detail="No matching key found")

        payload = jwt.decode(
            token,
            signing_key,
            algorithms=[alg],
            audience="authenticated",
        )
        # Email can be in different places depending on auth method
        email = (
            payload.get("email")
            or payload.get("user_metadata", {}).get("email")
            or payload.get("app_metadata", {}).get("email")
            or ""
        )
        return {"id": payload["sub"], "email": email}

    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch JWKS: {e}")
