import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.database import engine, init_db
from app.routes.songs import router as songs_router
from app.routes.youtube import router as youtube_router
from app.schemas import HealthResponse

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("aawaz.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown routines."""
    logger.info("Initializing AAWAZ Backend...")
    try:
        init_db()
        logger.info("Database initialized successfully.")
    except Exception as exc:
        logger.error(f"Error during database initialization: {exc}")
    yield
    logger.info("MUSIFY Backend shutting down...")


app = FastAPI(
    title="MUSIFY API",
    description=(
        "Backend API for MUSIFY: Discover & Stream Indian and Regional Music. "
        "Provides YouTube search discovery, song catalog metadata, and range-supported audio streaming."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS Configuration
# Production origins configured strictly via CORS_ORIGINS environment variable.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https://.*(\.onrender\.com|\.pages\.dev|\.app\.dev)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Range", "Accept-Ranges", "Content-Length", "Content-Type"],
)

# Register Routers
app.include_router(songs_router)
app.include_router(youtube_router)


# ==========================================
# HEALTH CHECK & ROOT ENDPOINTS
# ==========================================

@app.get("/", tags=["Health"])
def root():
    """Root endpoint for Render default health checks and load balancers."""
    return {"message": "MUSIFY API is live", "status": "ok", "health": "/health"}


@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health_check():
    """Simple health check endpoint for cloud load balancers and orchestrators."""
    return HealthResponse(status="ok")


@app.get("/api/status", tags=["Health"])
def status_endpoint():
    """Status endpoint reporting live environment configuration without leaking secrets."""
    from app.services.youtube_service import get_youtube_service
    yt_svc = get_youtube_service()
    has_yt = bool(yt_svc.api_key)
    return {
        "status": "ok",
        "backend": "live",
        "youtube_api_configured": has_yt,
        "youtube_key_prefix": yt_svc.api_key[:4] + "..." if has_yt else None,
        "cors_origins": settings.CORS_ORIGINS,
    }


@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
def api_health_check():
    """Detailed health check validating database connectivity."""
    db_status = "connected"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        logger.warning(f"Database health check failed: {exc}")
        db_status = f"error: {exc}"

    return HealthResponse(
        status="ok" if db_status == "connected" else "degraded",
        database=db_status,
    )
