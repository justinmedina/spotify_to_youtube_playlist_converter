# models.py
from sqlalchemy import String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from database import Base


class Track(Base):
    __tablename__ = "tracks"

    spotify_id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    artist: Mapped[str] = mapped_column(String, nullable=False)
    added_at: Mapped[str] = mapped_column(String, nullable=True)  # ISO string
    isrc: Mapped[str] = mapped_column(String, nullable=True)

    youtube_video_id: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")  # pending|matched|added|failed
    fail_reason: Mapped[str] = mapped_column(Text, nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class KV(Base):
    __tablename__ = "kv"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String, nullable=False)


class OAuthToken(Base):
    __tablename__ = "oauth_tokens"

    service: Mapped[str] = mapped_column(String, primary_key=True)  # spotify | google
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=True)
    token_type: Mapped[str] = mapped_column(String, nullable=True)
    scope: Mapped[str] = mapped_column(Text, nullable=True)
    expires_at: Mapped[str] = mapped_column(String, nullable=True)  # ISO string timestamp
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

