# spotify_client.py
import os
import base64
from datetime import datetime, timedelta
import httpx
from sqlalchemy.orm import Session
from models import OAuthToken

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

TOKEN_URL = "https://accounts.spotify.com/api/token"
API_BASE = "https://api.spotify.com/v1"


def _basic_auth_header():
    raw = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()
    return base64.b64encode(raw).decode()


async def get_spotify_access_token(db: Session) -> str:
    tok = db.get(OAuthToken, "spotify")
    if not tok:
        raise RuntimeError("Spotify not authorized yet. Visit /auth/spotify/login first.")

    # If expires_at missing, just try current token
    if tok.expires_at:
        try:
            if datetime.utcnow() < datetime.fromisoformat(tok.expires_at):
                return tok.access_token
        except Exception:
            pass

    if not tok.refresh_token:
        return tok.access_token

    headers = {"Authorization": f"Basic {_basic_auth_header()}"}
    data = {"grant_type": "refresh_token", "refresh_token": tok.refresh_token}

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(TOKEN_URL, data=data, headers=headers)
        r.raise_for_status()
        body = r.json()

    tok.access_token = body["access_token"]
    tok.token_type = body.get("token_type", tok.token_type)
    tok.scope = body.get("scope", tok.scope)
    tok.expires_at = (datetime.utcnow() + timedelta(seconds=int(body.get("expires_in", 3600)))).isoformat()
    db.commit()

    return tok.access_token


async def spotify_get(db: Session, path: str, params: dict | None = None) -> dict:
    access_token = await get_spotify_access_token(db)
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{API_BASE}{path}", headers=headers, params=params)
        r.raise_for_status()
        return r.json()

