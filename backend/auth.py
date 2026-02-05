"""Simple Supabase token verification helper.
- Uses SUPABASE_URL and SUPABASE_KEY environment variables
- GET /auth/v1/user with Authorization header returns user info when token is valid
"""
import os
import requests
from fastapi import Header, HTTPException

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


def get_user_from_token(token: str):
    """Return user dict from Supabase auth if token valid, else None."""
    if not SUPABASE_URL or not SUPABASE_KEY or not token:
        return None
    headers = {"Authorization": f"Bearer {token}", "apikey": SUPABASE_KEY}
    try:
        resp = requests.get(f"{SUPABASE_URL}/auth/v1/user", headers=headers, timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        return None
    return None


def get_current_user(authorization: str = Header(None)):
    """FastAPI dependency to get current user or raise 401 if token invalid.
    If no Authorization header is provided, return None (endpoints can make auth optional).
    """
    if not authorization:
        return None
    # header may be 'Bearer <token>' or just token
    token = authorization.split("Bearer ")[-1] if "Bearer " in authorization else authorization
    user = get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user
