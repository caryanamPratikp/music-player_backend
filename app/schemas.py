from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class SongBase(BaseModel):
    title: str = Field(..., examples=["Tu Aani Mi"])
    artist_name: str = Field(..., examples=["Demo Artist"])
    album_name: Optional[str] = Field(None, examples=["Independent"])
    language: Optional[str] = Field(None, examples=["Marathi"])
    genre: Optional[str] = Field(None, examples=["Indie"])

class SongCreate(SongBase):
    audio_url: str = Field(..., examples=["/media/music/tu-aani-mi.mp3"])
    cover_image_url: Optional[str] = Field(None, examples=["/media/covers/tu-aani-mi.jpg"])
    duration: Optional[int] = Field(0, examples=[213])

class SongResponse(SongBase):
    id: int
    cover_image_url: Optional[str] = None
    audio_url: str
    duration: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class HealthResponse(BaseModel):
    status: str
    database: Optional[str] = None
    version: str = "0.1.0"

class YouTubeItem(BaseModel):
    video_id: str
    title: str
    channel_title: str
    description: str = ""
    thumbnail: str = ""
    published_at: str = ""

class YouTubeSearchResponse(BaseModel):
    items: list[YouTubeItem]
    next_page_token: Optional[str] = None
    total_results: Optional[int] = None
