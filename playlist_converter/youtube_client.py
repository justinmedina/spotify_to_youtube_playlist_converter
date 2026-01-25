# youtube_client.py
import os
import asyncio
from datetime import datetime, timedelta

import httpx
from dotenv import load_dotenv
from sqlalchemy.orm import Session

from models import OAuthToken

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

TOKEN_URL = "https://oauth2.googleapis.com/token"
YT_BASE = "https://www.googleapis.com/youtube/v3"


async def get_google_access_token(db: Session) -> str:
    """
    Returns a valid Google access token, refreshing via refresh_token if needed.
    Tokens are stored in the oauth_tokens table with service='google'.
    """
    tok = db.get(OAuthToken, "google")
    if not tok:
        raise RuntimeError("Google not authorized yet. Visit /auth/google/login first.")

    # If we have a non-expired token, use it
    if tok.expires_at:
        try:
            if datetime.utcnow() < datetime.fromisoformat(tok.expires_at):
                return tok.access_token
        except Exception:
            # If expires_at is malformed, we attempt refresh below
            pass

    # If no refresh token, we can only try current token
    if not tok.refresh_token:
        return tok.access_token

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise RuntimeError("Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET in environment.")

    data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": tok.refresh_token,
        "grant_type": "refresh_token",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(TOKEN_URL, data=data)
        if r.status_code >= 400:
            raise RuntimeError(f"Google token refresh failed {r.status_code}: {r.text}")
        body = r.json()

    tok.access_token = body["access_token"]
    tok.token_type = body.get("token_type", tok.token_type)
    tok.scope = body.get("scope", tok.scope)
    tok.expires_at = (datetime.utcnow() + timedelta(seconds=int(body.get("expires_in", 3600)))).isoformat()
    db.commit()

    return tok.access_token


async def yt_get(db: Session, path: str, params: dict) -> dict:
    """
    GET wrapper for YouTube Data API that surfaces full error body on failure.
    """
    token = await get_google_access_token(db)
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{YT_BASE}{path}", headers=headers, params=params)

        if r.status_code >= 400:
            raise RuntimeError(f"YouTube GET {path} failed {r.status_code}: {r.text}")

        return r.json()


async def yt_post(db: Session, path: str, params: dict, json_body: dict) -> dict:
    """
    POST wrapper for YouTube Data API that surfaces full error body on failure.
    """
    token = await get_google_access_token(db)
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{YT_BASE}{path}", headers=headers, params=params, json=json_body)

        if r.status_code >= 400:
            raise RuntimeError(f"YouTube POST {path} failed {r.status_code}: {r.text}")

        return r.json()


async def youtube_search_best(
    db: Session,
    query: str,
    max_results: int = 3,
    sleep_seconds: float = 0.15,
) -> str | None:
    """
    Search YouTube for a query and return the first videoId (best-effort).
    """
    if sleep_seconds and sleep_seconds > 0:
        await asyncio.sleep(sleep_seconds)

    data = await yt_get(
        db,
        "/search",
        params={
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": max_results,
            "safeSearch": "none",
        },
    )

    items = data.get("items", [])
    if not items:
        return None

    vid = items[0].get("id", {}).get("videoId")
    return vid


async def youtube_create_playlist(
    db: Session,
    title: str,
    description: str = "Imported from Spotify Liked Songs",
    privacy: str = "private",
) -> str:
    """
    Create a YouTube playlist. Returns playlist ID.
    privacy: private | unlisted | public
    """
    data = await yt_post(
        db,
        "/playlists",
        params={"part": "snippet,status"},
        json_body={
            "snippet": {"title": title, "description": description},
            "status": {"privacyStatus": privacy},
        },
    )
    return data["id"]


async def youtube_add_to_playlist(db: Session, playlist_id: str, video_id: str) -> None:
    """
    Add a video to a YouTube playlist.
    """
    await yt_post(
        db,
        "/playlistItems",
        params={"part": "snippet"},
        json_body={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {"kind": "youtube#video", "videoId": video_id},
            }
        },
    )

