# AAWAZ Backend API (MVP / Proof of Concept)

FastAPI backend service powering the AAWAZ Indian independent music platform MVP.

## Features
- **FastAPI** modular routes for song catalog metadata (`/api/songs`, `/api/songs/{id}`).
- **HTTP 206 Partial Content Range Streaming** (`/media/music/{filename}`): enables browser audio players to buffer ahead, play, and seek accurately.
- **Pluggable Storage Abstraction** (`StorageService`): easily migrate between local disk (`LocalStorageService`) and cloud object storage (`CloudStorageService` - S3 / R2 / Supabase) in Phase 2.
- **MySQL 8.0 & SQLite Support**: uses PyMySQL with automatic DB provisioning, fallback-ready.
- **Dev-Only File Upload** (`POST /api/songs/upload`): easily upload tracks and album art during testing.
- **Health Checks**: `/health` and `/api/health`.

## Setup & Running

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.14)
- MySQL 8.0 running (default port `3307` or configure in `.env`)

### 2. Environment Configuration
Copy `.env.example` to `.env` and set your credentials:
```bash
cp .env.example .env
```
Default `.env`:
```env
DATABASE_URL=mysql+pymysql://root:root@localhost:3307/aawaz_db
PORT=8000
HOST=0.0.0.0
MUSIC_STORAGE_PATH=./music
COVER_STORAGE_PATH=./covers
STORAGE_BACKEND=local
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Seed Sample Dataset
Synthesizes 4 melodic audio tracks and album covers, and initializes the database:
```bash
python seed.py --force
```

### 5. Start Development Server
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
Interactive Swagger docs: `http://localhost:8000/docs`

### 6. Run Tests
```bash
python -m pytest tests -v
```
