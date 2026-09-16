from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base

def get_utc_now():
    return datetime.now(timezone.utc)

class Song(Base):
    """
    Song model representing audio tracks in AAWAZ.
    Kept intentionally lean for Phase 1 MVP (artist_name is a direct string).
    """
    __tablename__ = "songs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(255), nullable=False, index=True)
    artist_name = Column(String(255), nullable=False, index=True)
    album_name = Column(String(255), nullable=True)
    language = Column(String(100), nullable=True, index=True)
    genre = Column(String(100), nullable=True, index=True)
    cover_image_url = Column(String(500), nullable=True)
    audio_url = Column(String(500), nullable=False)
    duration = Column(Integer, default=0, nullable=False)  # Duration in seconds
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "artist_name": self.artist_name,
            "album_name": self.album_name,
            "language": self.language,
            "genre": self.genre,
            "cover_image_url": self.cover_image_url,
            "audio_url": self.audio_url,
            "duration": self.duration,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
