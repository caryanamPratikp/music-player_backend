"""
Aawaz Seed Script
Generates royalty-free synthesized audio tracks and aesthetic album covers,
then seeds them into the MySQL/SQLite database.
"""

import math
import os
import struct
import wave
from pathlib import Path
from datetime import datetime

# Adjust path so app modules can be imported
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.config import settings
from app.database import SessionLocal, init_db
from app.models import Song
from app.services.storage import get_storage_service


def generate_synthesized_track(filename: str, melody_type: str, duration_sec: int = 20) -> Path:
    """
    Synthesize an pleasant, musical harmonic audio track into standard 16-bit 44.1kHz stereo WAV.
    """
    file_path = settings.MUSIC_STORAGE_PATH / filename
    sample_rate = 44100
    num_samples = sample_rate * duration_sec

    # Define musical scales / chord progressions (frequencies in Hz)
    scales = {
        "indie_acoustic": [
            # D Major chords: D (146.83, 293.66), F# (185.00, 369.99), A (220.00, 440.00), B (246.94)
            (293.66, 369.99, 440.00),
            (246.94, 293.66, 369.99),
            (196.00, 246.94, 293.66),
            (220.00, 277.18, 329.63),
        ],
        "folk_fusion": [
            # E Minor / Folk modal progression
            (329.63, 392.00, 493.88),
            (261.63, 329.63, 392.00),
            (293.66, 369.99, 440.00),
            (246.94, 311.13, 369.99),
        ],
        "lofi_indie": [
            # Mellow Neo-soul / Lo-fi 7th chords: Cmaj7, Am7, Dm7, G7
            (261.63, 329.63, 392.00, 493.88),
            (220.00, 261.63, 329.63, 392.00),
            (146.83, 220.00, 261.63, 349.23),
            (196.00, 246.94, 293.66, 349.23),
        ],
        "indie_pop": [
            # Bright G - D - Em - C progression
            (196.00, 246.94, 293.66, 392.00),
            (146.83, 220.00, 293.66, 369.99),
            (164.81, 196.00, 246.94, 329.63),
            (130.81, 164.81, 196.00, 261.63),
        ],
    }

    progression = scales.get(melody_type, scales["indie_acoustic"])
    chord_len_sec = duration_sec / len(progression)

    with wave.open(str(file_path), "wb") as wav:
        wav.setnchannels(2)  # Stereo
        wav.setsampwidth(2)  # 16-bit
        wav.setframerate(sample_rate)

        frames = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            chord_idx = int(t / chord_len_sec) % len(progression)
            chord = progression[chord_idx]

            # Envelope for each chord note to prevent clicking
            t_in_chord = t % chord_len_sec
            envelope = math.sin(math.pi * (t_in_chord / chord_len_sec)) ** 0.5

            # Main harmonic voice
            voice_val = 0.0
            for note_idx, freq in enumerate(chord):
                # Subtle vibrato
                vibrato = 1.0 + 0.003 * math.sin(2 * math.pi * 5.0 * t)
                # Primary sine + gentle overtone
                note_val = math.sin(2 * math.pi * freq * vibrato * t)
                note_val += 0.3 * math.sin(4 * math.pi * freq * vibrato * t)
                voice_val += note_val

            voice_val = (voice_val / len(chord)) * envelope

            # Ambient low pad drone
            pad_val = 0.25 * math.sin(2 * math.pi * (chord[0] * 0.5) * t)

            # Left/Right spatial panning
            pan_l = 0.5 + 0.2 * math.sin(2 * math.pi * 0.2 * t)
            pan_r = 1.0 - pan_l

            sample_l = int(max(-1.0, min(1.0, (voice_val + pad_val) * pan_l * 0.65)) * 32767)
            sample_r = int(max(-1.0, min(1.0, (voice_val + pad_val) * pan_r * 0.65)) * 32767)

            frames.extend(struct.pack("<hh", sample_l, sample_r))

        wav.writeframes(frames)

    return file_path


def generate_album_cover(filename: str, title: str, artist: str, gradient_colors: tuple) -> Path:
    """
    Generate a modern, high-res dark music album cover in SVG format.
    """
    file_path = settings.COVER_STORAGE_PATH / filename
    col1, col2, col3 = gradient_colors

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500" width="500" height="500">
  <defs>
    <linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{col1}" />
      <stop offset="50%" stop-color="{col2}" />
      <stop offset="100%" stop-color="{col3}" />
    </linearGradient>
    <linearGradient id="overlay" x1="0%" y1="100%" x2="0%" y2="0%">
      <stop offset="0%" stop-color="rgba(10, 15, 29, 0.95)" />
      <stop offset="60%" stop-color="rgba(10, 15, 29, 0.4)" />
      <stop offset="100%" stop-color="rgba(10, 15, 29, 0.1)" />
    </linearGradient>
    <filter id="glow">
      <feGaussianBlur stdDeviation="15" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>
  
  <!-- Background Gradient -->
  <rect width="500" height="500" fill="url(#grad)" />
  
  <!-- Decorative Geometric Shapes -->
  <circle cx="250" cy="210" r="120" fill="none" stroke="rgba(255,255,255,0.15)" stroke-width="2" />
  <circle cx="250" cy="210" r="85" fill="none" stroke="rgba(255,255,255,0.25)" stroke-width="3" stroke-dasharray="8 6" />
  <circle cx="250" cy="210" r="45" fill="rgba(255,255,255,0.2)" filter="url(#glow)" />
  
  <!-- Audio Waveform Graphic -->
  <g transform="translate(160, 195)" fill="rgba(255,255,255,0.9)">
    <rect x="0" y="10" width="6" height="20" rx="3" />
    <rect x="15" y="0" width="6" height="40" rx="3" />
    <rect x="30" y="5" width="6" height="30" rx="3" />
    <rect x="45" y="-12" width="6" height="64" rx="3" />
    <rect x="60" y="-5" width="6" height="50" rx="3" />
    <rect x="75" y="10" width="6" height="20" rx="3" />
    <rect x="90" y="-8" width="6" height="56" rx="3" />
    <rect x="105" y="5" width="6" height="30" rx="3" />
    <rect x="120" y="0" width="6" height="40" rx="3" />
    <rect x="135" y="12" width="6" height="16" rx="3" />
    <rect x="150" y="14" width="6" height="12" rx="3" />
    <rect x="165" y="8" width="6" height="24" rx="3" />
  </g>
  
  <!-- Gradient Overlay for Typography Contrast -->
  <rect width="500" height="500" fill="url(#overlay)" />
  
  <!-- Top Brand Badge -->
  <rect x="36" y="36" width="76" height="26" rx="13" fill="rgba(255,255,255,0.15)" />
  <text x="74" y="53" fill="#ffffff" font-size="12" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-weight="700" text-anchor="middle" letter-spacing="2">AAWAZ</text>
  
  <!-- Song & Artist Details -->
  <text x="36" y="415" fill="#ffffff" font-size="28" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-weight="800">{title}</text>
  <text x="36" y="445" fill="rgba(255,255,255,0.75)" font-size="16" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-weight="500">{artist}</text>
</svg>"""

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(svg_content)

    return file_path


def seed_database(force: bool = False):
    """
    Main seeding routine: creates sample audio, covers, and database records.
    """
    print("=" * 60)
    print("AAWAZ Music Player MVP — Database Seeder")
    print("=" * 60)

    # 1. Initialize tables
    init_db()
    db = SessionLocal()

    try:
        existing_count = db.query(Song).count()
        if existing_count > 0 and not force:
            print(f"Database already contains {existing_count} songs. Skipping seed (use force=True to reseed).")
            return

        if force and existing_count > 0:
            print(f"Clearing {existing_count} existing songs for reseed...")
            db.query(Song).delete()
            db.commit()

        # 2. Sample Dataset Definitions
        sample_songs = [
            {
                "title": "Tu Aani Mi",
                "artist_name": "Demo Indie Ensemble",
                "album_name": "Independent Roots",
                "language": "Marathi",
                "genre": "Indie Acoustic",
                "audio_file": "tu-aani-mi.wav",
                "cover_file": "tu-aani-mi.svg",
                "melody_type": "indie_acoustic",
                "duration": 20,
                "gradient": ("#f59e0b", "#ec4899", "#6366f1"),
            },
            {
                "title": "Pahila Paus",
                "artist_name": "Sahyadri Strings",
                "album_name": "Monsoon Melodies",
                "language": "Marathi",
                "genre": "Folk Fusion",
                "audio_file": "pahila-paus.wav",
                "cover_file": "pahila-paus.svg",
                "melody_type": "folk_fusion",
                "duration": 22,
                "gradient": ("#059669", "#0284c7", "#1e1b4b"),
            },
            {
                "title": "Raat Ke Musafir",
                "artist_name": "Dilli Underground",
                "album_name": "Neon Midnight",
                "language": "Hindi",
                "genre": "Lo-Fi Indie",
                "audio_file": "raat-ke-musafir.wav",
                "cover_file": "raat-ke-musafir.svg",
                "melody_type": "lofi_indie",
                "duration": 24,
                "gradient": ("#7c3aed", "#db2777", "#18181b"),
            },
            {
                "title": "Baarishein Aur Chai",
                "artist_name": "Kabir & The Chaiwalas",
                "album_name": "Acoustic Evenings",
                "language": "Hindi",
                "genre": "Indie Pop",
                "audio_file": "baarishein-aur-chai.wav",
                "cover_file": "baarishein-aur-chai.svg",
                "melody_type": "indie_pop",
                "duration": 21,
                "gradient": ("#ea580c", "#d97706", "#451a03"),
            },
        ]

        print("\n1. Generating synthesized media files...")
        for item in sample_songs:
            # Generate Audio
            audio_path = generate_synthesized_track(
                filename=item["audio_file"],
                melody_type=item["melody_type"],
                duration_sec=item["duration"],
            )
            print(f"  [AUDIO] Generated: {audio_path.name} ({item['duration']}s)")

            # Generate Cover Art
            cover_path = generate_album_cover(
                filename=item["cover_file"],
                title=item["title"],
                artist=item["artist_name"],
                gradient_colors=item["gradient"],
            )
            print(f"  [COVER] Generated: {cover_path.name}")

            # Create Database Record
            song_record = Song(
                title=item["title"],
                artist_name=item["artist_name"],
                album_name=item["album_name"],
                language=item["language"],
                genre=item["genre"],
                audio_url=f"/media/music/{item['audio_file']}",
                cover_image_url=f"/media/covers/{item['cover_file']}",
                duration=item["duration"],
            )
            db.add(song_record)

        db.commit()
        print(f"\nSuccessfully seeded {len(sample_songs)} songs into the database!")

    finally:
        db.close()


if __name__ == "__main__":
    force_seed = "--force" in sys.argv
    seed_database(force=force_seed)
