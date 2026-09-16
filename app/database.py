import logging
import re
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

logger = logging.getLogger("aawaz.database")

Base = declarative_base()

def ensure_database_exists(db_url: str):
    """
    For MySQL connections, ensure the target database exists.
    If not, create it before initializing the engine.
    """
    if not db_url.startswith("mysql"):
        return

    try:
        import pymysql
        # Parse connection details from db_url
        # Format: mysql+pymysql://user:password@host:port/dbname
        pattern = r"mysql(?:\+pymysql)?://([^:]+):([^@]+)@([^:/]+)(?::(\d+))?/([^?]+)"
        match = re.match(pattern, db_url)
        if match:
            user, password, host, port, dbname = match.groups()
            port = int(port) if port else 3306
            
            logger.info(f"Connecting to MySQL server at {host}:{port} to verify database '{dbname}'...")
            conn = pymysql.connect(
                host=host,
                user=user,
                password=password,
                port=port,
                charset="utf8mb4"
            )
            with conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{dbname}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
            conn.commit()
            conn.close()
            logger.info(f"Database '{dbname}' is ready.")
    except Exception as exc:
        logger.warning(f"Could not verify/create MySQL database automatically: {exc}. Proceeding with standard engine.")

# Ensure DB exists if MySQL
ensure_database_exists(settings.DATABASE_URL)

# Engine setup
engine_kwargs = {"pool_pre_ping": True}
if settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """FastAPI dependency for obtaining a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Create all tables defined in models."""
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified/created successfully.")
