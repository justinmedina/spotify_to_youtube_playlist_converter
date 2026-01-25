# google_auth.py
import os
from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from models import OAuthToken

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

YOUTUBE_SCOPES = os.getenv("YOUTUBE_SCOPES", "https://www.googleapis.com/auth/youtube")

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"


@router.get("/login")
def google_login():
    if not GOOGLE_CLIENT_ID or not GOOGLE_REDIRECT_URI:
        raise HTTPException(500, "Missing GOOGLE_CLIENT_ID or GOOGLE_REDIRECT_URI")

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": YOUTUBE_SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    return RedirectResponse(f"{AUTH_URL}?{urlencode(params)}")


@router.get("/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    code = request.query_params.get("code")
    error = request.query_params.get("error")

    if error:
        return JSONResponse({"error": error}, status_code=400)
    if not code:
        return JSONResponse({"error": "missing_code"}, status_code=400)

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(500, "Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET")

    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(TOKEN_URL, data=data)
        if r.status_code != 200:
            raise HTTPException(r.status_code, f"Google token error: {r.text}")
        tok = r.json()

    expires_at = (datetime.utcnow() + timedelta(seconds=int(tok.get("expires_in", 3600)))).isoformat()

    existing = db.get(OAuthToken, "google")
    if existing:
        existing.access_token = tok["access_token"]
        existing.refresh_token = tok.get("refresh_token") or existing.refresh_token
        existing.token_type = tok.get("token_type")
        existing.scope = tok.get("scope")
        existing.expires_at = expires_at
    else:
        db.add(
            OAuthToken(
                service="google",
                access_token=tok["access_token"],
                refresh_token=tok.get("refresh_token"),
                token_type=tok.get("token_type"),
                scope=tok.get("scope"),
                expires_at=expires_at,
            )
        )

    db.commit()
    return RedirectResponse(url="/", status_code=302)

