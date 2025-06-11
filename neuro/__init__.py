"""Neuro-sings python package.

This file contains the main paths definitions"""

from pathlib import Path

ROOT = Path(".")

DATA_ROOT = ROOT / Path("data")

SONGS_JSON = DATA_ROOT / "songs_new.json"
SONGS_CSV = DATA_ROOT / "songs.csv"

DATES_CSV = DATA_ROOT / "dates.csv"
DATES_OLD_CSV = DATA_ROOT / "dates_v12.csv"

IMAGES_ROOT = ROOT / Path("images")
IMAGES_BG = IMAGES_ROOT / "bg"
IMAGES_DATES = IMAGES_ROOT / "dates"
IMAGES_COVERS = IMAGES_ROOT / "cover"
IMAGES_CUSTOM = IMAGES_ROOT / "custom"

SONG_ROOT = ROOT / Path("songs")
DRIVE_ROOT = SONG_ROOT / "drive"
CUSTOM_ROOT = SONG_ROOT / "custom"

LOG_DIR = ROOT / Path("logs")
