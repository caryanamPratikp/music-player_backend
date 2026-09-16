import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas import YouTubeSearchResponse
from app.services.youtube_service import YouTubeService, get_youtube_service

logger = logging.getLogger("aawaz.routes.youtube")

router = APIRouter(prefix="/api/youtube", tags=["YouTube Music"])


@router.get(
    "/search",
    response_model=YouTubeSearchResponse,
    summary="Search YouTube videos for music discovery",
)
async def search_youtube(
    q: str = Query(..., min_length=1, description="Search query string (e.g. 'Arijit Singh', 'Marathi songs')"),
    max_results: int = Query(10, ge=1, le=50, description="Maximum number of results to return (default 10)"),
    page: Optional[str] = Query(None, description="Pagination token (optional)"),
    youtube_service: YouTubeService = Depends(get_youtube_service),
):
    """
    Search YouTube videos via YouTube Data API v3.
    Returns cleaned items with video_id, title, channel_title, and thumbnail.
    Keeps API key secure on the backend and enforces quota protections.
    """
    clean_q = q.strip()
    if not clean_q:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty",
        )

    results = await youtube_service.search_videos(
        query=clean_q,
        max_results=max_results,
        page_token=page,
    )
    return results
