import os
from pathlib import Path
from typing import List

# Base directory for backend (where .env lives)
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables if .env exists
try:
    from dotenv import load_dotenv
    env_file = BASE_DIR / ".env"
    if env_file.exists():
        load_dotenv(dotenv_path=env_file)
    else:
        load_dotenv()
except ImportError:
    pass

class Settings:
    def __init__(self):
        # Load from environment, fallback to defaults
        self.DATABASE_URL: str = os.getenv(
            "DATABASE_URL",
            "mysql+pymysql://root:root@localhost:3307/aawaz_db"
        )
        self.PORT: int = int(os.getenv("PORT", "8000"))
        self.HOST: str = os.getenv("HOST", "0.0.0.0")
        
        # Storage paths
        raw_music_path = os.getenv("MUSIC_STORAGE_PATH", "./music")
        self.MUSIC_STORAGE_PATH: Path = (
            Path(raw_music_path) if Path(raw_music_path).is_absolute()
            else (BASE_DIR / raw_music_path).resolve()
        )
        
        raw_cover_path = os.getenv("COVER_STORAGE_PATH", "./covers")
        self.COVER_STORAGE_PATH: Path = (
            Path(raw_cover_path) if Path(raw_cover_path).is_absolute()
            else (BASE_DIR / raw_cover_path).resolve()
        )
        
        self.STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "local")
        
        # CORS allowed origins
        cors_raw = os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://localhost:3000,https://music-player-frontend-3gwn.onrender.com,https://musify.pages.dev,https://musify.app.dev"
        )
        self.CORS_ORIGINS: List[str] = [
            origin.strip() for origin in cors_raw.split(",") if origin.strip()
        ]

        # YouTube API Configuration
        self.YOUTUBE_API_KEY: str = os.getenv("YOUTUBE_API_KEY", "")
        
        # Ensure local storage paths exist
        self.MUSIC_STORAGE_PATH.mkdir(parents=True, exist_ok=True)
        self.COVER_STORAGE_PATH.mkdir(parents=True, exist_ok=True)

settings = Settings()
