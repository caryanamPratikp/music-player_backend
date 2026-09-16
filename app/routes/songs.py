import mimetypes
import os
import re
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Header,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Song
from app.schemas import SongCreate, SongResponse
from app.services.storage import StorageService, get_storage_service

router = APIRouter()

# Validation Constants
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".flac"}
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".svg"}
MAX_AUDIO_SIZE = 50 * 1024 * 1024  # 50 MB
MAX_IMAGE_SIZE = 10 * 1024 * 1024   # 10 MB

AUDIO_MIME_TYPES = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".m4a": "audio/mp4",
    ".flac": "audio/flac",
}


# ==========================================
# 1. SONG CRUD ENDPOINTS
# ==========================================

@router.get("/api/songs", response_model=List[SongResponse], tags=["Songs"])
def list_songs(db: Session = Depends(get_db)):
    """
    Retrieve all songs currently in the library.
    Returns metadata including audio_url and cover_image_url.
    """
    return db.query(Song).order_by(Song.id.asc()).all()


@router.get("/api/songs/{song_id}", response_model=SongResponse, tags=["Songs"])
def get_song(song_id: int, db: Session = Depends(get_db)):
    """
    Retrieve details for a single song by its ID.
    """
    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Song with ID {song_id} not found")
    return song


@router.post("/api/songs", response_model=SongResponse, status_code=status.HTTP_201_CREATED, tags=["Songs"])
def create_song(song_in: SongCreate, db: Session = Depends(get_db)):
    """
    Create a new song record with existing audio/cover URLs.
    Does not require file upload (useful for testing or referencing external URLs).
    """
    new_song = Song(
        title=song_in.title,
        artist_name=song_in.artist_name,
        album_name=song_in.album_name,
        language=song_in.language,
        genre=song_in.genre,
        audio_url=song_in.audio_url,
        cover_image_url=song_in.cover_image_url,
        duration=song_in.duration or 0,
    )
    db.add(new_song)
    db.commit()
    db.refresh(new_song)
    return new_song


# ==========================================
# 2. DEVELOPMENT FILE UPLOAD ENDPOINT
# ==========================================

@router.post(
    "/api/songs/upload",
    response_model=SongResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Development Only"],
    summary="[DEV ONLY] Upload an audio file and optional cover art",
)
async def upload_song_dev(
    audio_file: UploadFile = File(..., description="Audio file (.mp3, .wav, .ogg, .m4a)"),
    cover_file: Optional[UploadFile] = File(None, description="Cover image (.jpg, .jpeg, .png, .webp)"),
    title: str = Form(..., description="Song title"),
    artist_name: str = Form(..., description="Artist or Band name"),
    album_name: Optional[str] = Form(None, description="Album or Release name"),
    language: Optional[str] = Form(None, description="Language (e.g. Marathi, Hindi)"),
    genre: Optional[str] = Form(None, description="Genre (e.g. Indie, Folk, Rock)"),
    duration: Optional[int] = Form(None, description="Duration in seconds (calculated automatically if omitted)"),
    db: Session = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
):
    """
    DEVELOPMENT ONLY: Upload an audio track and cover art to local media storage
    and register a database record.
    Production will replace this with signed upload URLs to cloud object storage.
    """
    # 1. Validate Audio File
    audio_ext = Path(audio_file.filename).suffix.lower()
    if audio_ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported audio format '{audio_ext}'. Allowed formats: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}",
        )

    audio_bytes = await audio_file.read()
    if len(audio_bytes) > MAX_AUDIO_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Audio file exceeds maximum size of {MAX_AUDIO_SIZE // (1024*1024)}MB",
        )

    # 2. Extract Duration if not explicitly provided
    calculated_duration = duration or 0
    if not duration:
        try:
            import mutagen
            from io import BytesIO
            audio_info = mutagen.File(BytesIO(audio_bytes))
            if audio_info and hasattr(audio_info, "info") and audio_info.info.length:
                calculated_duration = int(round(audio_info.info.length))
        except Exception:
            calculated_duration = 0

    # 3. Save Audio File
    safe_uid = uuid.uuid4().hex[:10]
    clean_audio_title = re.sub(r"[^a-zA-Z0-9_-]", "-", title.lower()).strip("-") or "track"
    saved_audio_filename = f"{clean_audio_title}-{safe_uid}{audio_ext}"
    audio_url = storage.save_file(audio_bytes, saved_audio_filename, subfolder="music")

    # 4. Handle Optional Cover File
    cover_url = None
    if cover_file and cover_file.filename:
        cover_ext = Path(cover_file.filename).suffix.lower()
        if cover_ext not in ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported image format '{cover_ext}'. Allowed formats: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}",
            )
        cover_bytes = await cover_file.read()
        if len(cover_bytes) > MAX_IMAGE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cover image exceeds maximum size of {MAX_IMAGE_SIZE // (1024*1024)}MB",
            )
        saved_cover_filename = f"{clean_audio_title}-{safe_uid}{cover_ext}"
        cover_url = storage.save_file(cover_bytes, saved_cover_filename, subfolder="covers")

    # 5. Create Database Record
    song = Song(
        title=title.strip(),
        artist_name=artist_name.strip(),
        album_name=album_name.strip() if album_name else None,
        language=language.strip() if language else None,
        genre=genre.strip() if genre else None,
        cover_image_url=cover_url,
        audio_url=audio_url,
        duration=calculated_duration,
    )
    db.add(song)
    db.commit()
    db.refresh(song)
    return song


# ==========================================
# 3. MEDIA & HTTP RANGE STREAMING ENDPOINTS
# ==========================================

@router.get("/media/music/{filename}", tags=["Media Streaming"])
def stream_music(
    filename: str,
    request: Request,
    storage: StorageService = Depends(get_storage_service),
):
    """
    Stream audio files with full HTTP Range request support (RFC 7233).
    Enables HTML5 audio players to play, pause, buffer ahead, and seek
    without downloading the entire file into memory.
    """
    try:
        if not storage.file_exists(filename, subfolder="music"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Audio file '{filename}' not found")
        file_size = storage.get_file_size(filename, subfolder="music")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename")

    ext = Path(filename).suffix.lower()
    content_type = AUDIO_MIME_TYPES.get(ext, "application/octet-stream")

    range_header = request.headers.get("Range")

    # Case 1: Standard Full File Request (No Range Header)
    if not range_header:
        stream = storage.open_stream(filename, subfolder="music", start=0, end=file_size - 1)
        headers = {
            "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(file_size),
            "Content-Type": content_type,
        }
        return StreamingResponse(stream, status_code=status.HTTP_200_OK, headers=headers)

    # Case 2: HTTP Range Request (e.g. Range: bytes=0-1024 or bytes=1024-)
    range_match = re.match(r"bytes=(\d+)-(\d+)?", range_header)
    if not range_match:
        # Invalid format
        return Response(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    start_str, end_str = range_match.groups()
    start = int(start_str)
    end = int(end_str) if end_str else file_size - 1

    if start >= file_size or start > end:
        return Response(
            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
            headers={"Content-Range": f"bytes */{file_size}"},
        )

    end = min(end, file_size - 1)
    content_length = end - start + 1

    stream = storage.open_stream(filename, subfolder="music", start=start, end=end)

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(content_length),
        "Content-Type": content_type,
    }
    return StreamingResponse(
        stream,
        status_code=status.HTTP_206_PARTIAL_CONTENT,
        headers=headers,
    )


@router.get("/media/covers/{filename}", tags=["Media"])
def get_cover_image(
    filename: str,
    storage: StorageService = Depends(get_storage_service),
):
    """
    Serve cover art images directly with proper MIME type headers.
    """
    try:
        file_path = storage.get_file_path(filename, subfolder="covers")
        if not file_path or not file_path.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cover image not found")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename")

    content_type, _ = mimetypes.guess_type(str(file_path))
    return FileResponse(file_path, media_type=content_type or "image/jpeg")
