import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.main import app
from app.database import SessionLocal
from app.models import Song

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_api_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"


def test_get_all_songs():
    response = client.get("/api/songs")
    assert response.status_code == 200
    songs = response.json()
    assert isinstance(songs, list)
    assert len(songs) >= 4
    first_song = songs[0]
    assert "title" in first_song
    assert "artist_name" in first_song
    assert "audio_url" in first_song


def test_get_single_song():
    response = client.get("/api/songs/1")
    assert response.status_code == 200
    song = response.json()
    assert song["id"] == 1
    assert song["title"] == "Tu Aani Mi"
    assert song["language"] == "Marathi"


def test_get_nonexistent_song():
    response = client.get("/api/songs/99999")
    assert response.status_code == 404


def test_create_song_json():
    payload = {
        "title": "Test Track",
        "artist_name": "Indie Tester",
        "album_name": "Test EP",
        "language": "Hindi",
        "genre": "Acoustic",
        "audio_url": "/media/music/tu-aani-mi.wav",
        "cover_image_url": "/media/covers/tu-aani-mi.svg",
        "duration": 45,
    }
    response = client.post("/api/songs", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Track"
    assert data["id"] is not None

    # Clean up test song
    db = SessionLocal()
    db.query(Song).filter(Song.id == data["id"]).delete()
    db.commit()
    db.close()


def test_stream_music_full():
    response = client.get("/media/music/tu-aani-mi.wav")
    assert response.status_code == 200
    assert response.headers.get("Accept-Ranges") == "bytes"
    assert "audio" in response.headers.get("Content-Type")
    assert int(response.headers.get("Content-Length")) > 100000


def test_stream_music_range_request():
    headers = {"Range": "bytes=0-1023"}
    response = client.get("/media/music/tu-aani-mi.wav", headers=headers)
    assert response.status_code == 206
    assert response.headers.get("Accept-Ranges") == "bytes"
    assert response.headers.get("Content-Range").startswith("bytes 0-1023/")
    assert response.headers.get("Content-Length") == "1024"
    assert len(response.content) == 1024


def test_stream_music_invalid_range():
    headers = {"Range": "bytes=999999999-"}
    response = client.get("/media/music/tu-aani-mi.wav", headers=headers)
    assert response.status_code == 416


def test_get_cover_image():
    response = client.get("/media/covers/tu-aani-mi.svg")
    assert response.status_code == 200
    assert "image" in response.headers.get("Content-Type")
