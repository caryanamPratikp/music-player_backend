import logging
from typing import Dict, List, Optional
import httpx
from fastapi import HTTPException, status
from app.config import settings

logger = logging.getLogger("aawaz.youtube")

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"


class YouTubeService:
    """
    Service wrapper for YouTube Data API v3 search endpoint.
    Retrieves video metadata optimized for Indian music discovery.
    Strictly keeps API credentials on backend only.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.YOUTUBE_API_KEY

    async def search_videos(
        self,
        query: str,
        max_results: int = 10,
        page_token: Optional[str] = None,
    ) -> Dict:
        """
        Search YouTube videos by query.
        Transforms raw YouTube responses into clean, lightweight dictionaries.
        """
        if not self.api_key:
            logger.error("YOUTUBE_API_KEY is not configured in backend environment.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="YouTube service is not configured. Please set YOUTUBE_API_KEY in .env.",
            )

        clean_query = query.strip()
        if not clean_query:
            return {"items": [], "next_page_token": None}

        # Restrict max_results to 1..50 (default 10)
        bounded_max_results = max(1, min(50, max_results))

        params = {
            "part": "snippet",
            "type": "video",
            "q": clean_query,
            "maxResults": bounded_max_results,
            "regionCode": "IN",
            "relevanceLanguage": "hi",
            "key": self.api_key,
        }

        if page_token:
            params["pageToken"] = page_token

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(YOUTUBE_SEARCH_URL, params=params)

            if response.status_code == 200:
                data = response.json()
                items: List[Dict] = []

                for raw_item in data.get("items", []):
                    # Ensure it's a video
                    id_info = raw_item.get("id", {})
                    video_id = id_info.get("videoId")
                    if not video_id:
                        continue

                    snippet = raw_item.get("snippet", {})
                    thumbnails = snippet.get("thumbnails", {})

                    # Pick best available thumbnail: medium, high, or default
                    thumb_obj = (
                        thumbnails.get("medium")
                        or thumbnails.get("high")
                        or thumbnails.get("default")
                        or {}
                    )
                    thumbnail_url = thumb_obj.get("url", "")

                    items.append({
                        "video_id": video_id,
                        "title": snippet.get("title", "Untitled Track"),
                        "channel_title": snippet.get("channelTitle", "Unknown Artist"),
                        "description": snippet.get("description", ""),
                        "thumbnail": thumbnail_url,
                        "published_at": snippet.get("publishedAt", ""),
                    })

                return {
                    "items": items,
                    "next_page_token": data.get("nextPageToken"),
                    "total_results": data.get("pageInfo", {}).get("totalResults", len(items)),
                }

            # Handle non-200 responses from Google API
            error_json = {}
            try:
                error_json = response.json().get("error", {})
            except Exception:
                pass

            error_message = error_json.get("message", "YouTube API returned an error")
            errors_list = error_json.get("errors", [])
            reason = errors_list[0].get("reason", "") if errors_list else ""

            logger.warning(
                f"YouTube API error HTTP {response.status_code}: reason='{reason}', message='{error_message}'"
            )

            if response.status_code == 403:
                if "quota" in reason.lower() or "quota" in error_message.lower():
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="YouTube search quota exceeded for today. Please try again later.",
                    )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access forbidden by YouTube API. Check API key permissions.",
                )

            if response.status_code == 400:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid search request parameters.",
                )

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to search YouTube at this time.",
            )

        except httpx.TimeoutException:
            logger.error("Timeout while connecting to YouTube Data API.")
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="YouTube service timed out. Please check network and try again.",
            )
        except httpx.RequestError as exc:
            logger.error(f"Network error while connecting to YouTube: {exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Network error connecting to YouTube. Please try again.",
            )


# Singleton service provider
_youtube_service: Optional[YouTubeService] = None

def get_youtube_service() -> YouTubeService:
    global _youtube_service
    if _youtube_service is None:
        _youtube_service = YouTubeService()
    return _youtube_service
