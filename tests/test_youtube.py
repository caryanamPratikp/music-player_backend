import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.main import app

client = TestClient(app)


def test_youtube_search_missing_query():
    response = client.get("/api/youtube/search")
    assert response.status_code == 422  # Validation error (missing required parameter q)


def test_youtube_search_empty_query():
    response = client.get("/api/youtube/search?q=%20%20")
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_youtube_search_arijit_singh():
    response = client.get("/api/youtube/search?q=Arijit%20Singh&max_results=3")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    items = data["items"]
    assert len(items) > 0

    first = items[0]
    assert "video_id" in first
    assert "title" in first
    assert "channel_title" in first
    assert "thumbnail" in first
    assert len(first["video_id"]) > 5

    # Security check: ensure API key is never leaked in the response text or headers
    raw_response_text = response.text
    assert "AIzaSy" not in raw_response_text
    assert "key=" not in raw_response_text


def test_youtube_search_marathi_songs():
    response = client.get("/api/youtube/search?q=Marathi%20songs&max_results=3")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0
    assert "video_id" in data["items"][0]
