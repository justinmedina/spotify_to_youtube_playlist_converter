# routes.py
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Track, KV
from spotify_client import spotify_get
from youtube_client import (
    youtube_create_playlist,
    youtube_search_best,
    youtube_add_to_playlist,
)

router = APIRouter()

SPOTIFY_PAGE_SIZE = int(os.getenv("SPOTIFY_PAGE_SIZE", "50"))
SYNC_LIMIT = int(os.getenv("SYNC_LIMIT", "500"))

TRANSFER_LIMIT = int(os.getenv("TRANSFER_LIMIT", "200"))
YOUTUBE_SEARCH_RESULTS = int(os.getenv("YOUTUBE_SEARCH_RESULTS", "3"))
YOUTUBE_SLEEP_SECONDS = float(os.getenv("YOUTUBE_SLEEP_SECONDS", "0.15"))

# KV keys for storing the default playlist
PLAYLIST_ID_KEY = "yt_playlist_id_default"
PLAYLIST_TITLE_KEY = "yt_playlist_title_default"


@router.get("/spotify/sync_liked")
async def sync_spotify_liked(db: Session = Depends(get_db), limit: int | None = None):
    """
    Pull liked songs from Spotify in pages of 50 and store them in SQLite.
    """
    limit = limit or SYNC_LIMIT
    saved = 0
    offset = 0

    while saved < limit:
        page = await spotify_get(
            db,
            "/me/tracks",
            params={"limit": min(SPOTIFY_PAGE_SIZE, limit - saved), "offset": offset},
        )
        items = page.get("items", [])
        if not items:
            break

        for it in items:
            tr = it.get("track") or {}
            spotify_id = tr.get("id")
            if not spotify_id:
                continue

            title = tr.get("name") or ""
            artists = tr.get("artists") or []
            artist = artists[0]["name"] if artists else ""

            added_at = it.get("added_at")
            isrc = ((tr.get("external_ids") or {}).get("isrc"))

            # insert if not exists
            existing = db.get(Track, spotify_id)
            if not existing:
                db.add(
                    Track(
                        spotify_id=spotify_id,
                        title=title,
                        artist=artist,
                        added_at=added_at,
                        isrc=isrc,
                        status="pending",
                    )
                )
                saved += 1

        db.commit()
        offset += len(items)
        if len(items) < SPOTIFY_PAGE_SIZE:
            break

    return {"ok": True, "saved_new_tracks": saved, "offset_ended_at": offset}


def _get_kv(db: Session, key: str) -> str | None:
    row = db.get(KV, key)
    return row.value if row else None


def _set_kv(db: Session, key: str, value: str) -> None:
    row = db.get(KV, key)
    if row:
        row.value = value
    else:
        db.add(KV(key=key, value=value))


@router.post("/transfer/youtube")
async def transfer_to_youtube(
    db: Session = Depends(get_db),
    playlist_title: str = "Spotify Liked Songs",
    limit: int | None = None,
    new_playlist: bool = False,
):
    """
    Append up to N pending tracks to a YouTube playlist.

    Behavior:
    - By default, reuses the previously created playlist (stored in KV).
    - If new_playlist=true, creates a fresh playlist and stores it as the new default.
    - Only pulls Track.status == "pending" so you don't keep retrying failed tracks.
    """
    limit = limit or TRANSFER_LIMIT

    # pending only (recommended)
    pending = (
        db.query(Track)
        .filter(Track.status == "pending")
        .order_by(Track.added_at.desc().nullslast())
        .limit(limit)
        .all()
    )

    if not pending:
        return {"ok": True, "message": "No pending tracks to transfer."}

    # get-or-create playlist
    existing_playlist_id = _get_kv(db, PLAYLIST_ID_KEY)
    existing_title = _get_kv(db, PLAYLIST_TITLE_KEY)

    if (not new_playlist) and existing_playlist_id and (existing_title == playlist_title):
        playlist_id = existing_playlist_id
    else:
        try:
            playlist_id = await youtube_create_playlist(db, playlist_title)
        except Exception as e:
            raise HTTPException(500, f"Failed to create YouTube playlist: {e}")

        _set_kv(db, PLAYLIST_ID_KEY, playlist_id)
        _set_kv(db, PLAYLIST_TITLE_KEY, playlist_title)
        db.commit()

    added = 0
    matched = 0
    failed = 0

    for t in pending:
        try:
            # Find best YouTube video
            q = f"{t.artist} {t.title} official audio"
            vid = await youtube_search_best(
                db, q, max_results=YOUTUBE_SEARCH_RESULTS, sleep_seconds=YOUTUBE_SLEEP_SECONDS
            )

            if not vid:
                t.status = "failed"
                t.fail_reason = "No YouTube match found"
                failed += 1
                db.commit()
                continue

            t.youtube_video_id = vid
            t.status = "matched"
            matched += 1
            db.commit()

            # Add to playlist
            await youtube_add_to_playlist(db, playlist_id, t.youtube_video_id)
            t.status = "added"
            t.fail_reason = None
            added += 1
            db.commit()

        except Exception as e:
            t.status = "failed"
            t.fail_reason = str(e)[:500]
            failed += 1
            db.commit()

    return {
        "ok": True,
        "playlist_id": playlist_id,
        "playlist_title": playlist_title,
        "attempted": len(pending),
        "matched_new": matched,
        "added": added,
        "failed": failed,
        "new_playlist_created": new_playlist or (existing_playlist_id is None) or (existing_title != playlist_title),
    }
@router.get("/tracks/status_counts")
def status_counts(db: Session = Depends(get_db)):
    total = db.query(Track).count()
    pending = db.query(Track).filter(Track.status == "pending").count()
    matched = db.query(Track).filter(Track.status == "matched").count()
    added = db.query(Track).filter(Track.status == "added").count()
    failed = db.query(Track).filter(Track.status == "failed").count()
    return {"total": total, "pending": pending, "matched": matched, "added": added, "failed": failed}


@router.get("/tracks/failed")
def list_failed(db: Session = Depends(get_db), limit: int = 25):
    rows = (
        db.query(Track)
        .filter(Track.status == "failed")
        .order_by(Track.updated_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "spotify_id": r.spotify_id,
            "artist": r.artist,
            "title": r.title,
            "fail_reason": r.fail_reason,
        }
        for r in rows
    ]

