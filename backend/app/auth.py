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

    Uses Supabase's JWKS endpoint to get the public key for RS256 verification.
    Falls back to HS256 with SUPABASE_JWT_SECRET if set.
    """
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization token")

    token = auth_header.split(" ", 1)[1]

    # Try HS256 with legacy secret first (if configured)
    legacy_secret = os.environ.get("SUPABASE_JWT_SECRET", "")
    if legacy_secret:
        try:
            payload = jwt.decode(
                token,
                legacy_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
            return {"id": payload["sub"], "email": payload.get("email", "")}
        except JWTError:
            pass  # Fall through to JWKS

    # Use JWKS (new system)
    try:
        jwks = await _get_jwks()
        # Get the key ID from the token header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")

        # Find matching key
        rsa_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                rsa_key = key
                break

        if not rsa_key:
            raise HTTPException(status_code=401, detail="No matching key found")

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience="authenticated",
        )
        return {"id": payload["sub"], "email": payload.get("email", "")}

    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    except httpx.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch JWKS: {e}")
