# spotify_auth.py
import os
import base64
from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from models import OAuthToken

router = APIRouter()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
SPOTIFY_SCOPES = os.getenv("SPOTIFY_SCOPES", "user-library-read")

AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"


def _basic_auth_header():
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        raise HTTPException(500, "Missing SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET")
    raw = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()
    return base64.b64encode(raw).decode()


@router.get("/login")
def spotify_login():
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_REDIRECT_URI:
        raise HTTPException(500, "Missing SPOTIFY_CLIENT_ID or SPOTIFY_REDIRECT_URI")

    params = {
        "response_type": "code",
        "client_id": SPOTIFY_CLIENT_ID,
        "scope": SPOTIFY_SCOPES,
        "redirect_uri": SPOTIFY_REDIRECT_URI,
    }
    return RedirectResponse(f"{AUTH_URL}?{urlencode(params)}")


@router.get("/callback")
async def spotify_callback(request: Request, db: Session = Depends(get_db)):
    code = request.query_params.get("code")
    error = request.query_params.get("error")

    if error:
        return JSONResponse({"error": error}, status_code=400)
    if not code:
        return JSONResponse({"error": "missing_code"}, status_code=400)

    headers = {"Authorization": f"Basic {_basic_auth_header()}"}
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": SPOTIFY_REDIRECT_URI,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(TOKEN_URL, data=data, headers=headers)
        if r.status_code != 200:
            raise HTTPException(r.status_code, f"Spotify token error: {r.text}")
        tok = r.json()

    expires_at = (datetime.utcnow() + timedelta(seconds=int(tok.get("expires_in", 3600)))).isoformat()

    existing = db.get(OAuthToken, "spotify")
    if existing:
        existing.access_token = tok["access_token"]
        existing.refresh_token = tok.get("refresh_token") or existing.refresh_token
        existing.token_type = tok.get("token_type")
        existing.scope = tok.get("scope")
        existing.expires_at = expires_at
    else:
        db.add(
            OAuthToken(
                service="spotify",
                access_token=tok["access_token"],
                refresh_token=tok.get("refresh_token"),
                token_type=tok.get("token_type"),
                scope=tok.get("scope"),
                expires_at=expires_at,
            )
        )

    db.commit()
    return RedirectResponse(url="/", status_code=302)

