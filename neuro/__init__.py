"""Neuro-sings python package.

This file contains the main paths definitions."""

from pathlib import Path

ROOT_DIR = Path(".")

DATA_DIR = ROOT_DIR / Path("data")

SONGS_JSON = DATA_DIR / "songs_new.json"
SONGS_CSV = DATA_DIR / "songs.csv"
SONGS_DB = DATA_DIR / "songs.db"

DATES_CSV = DATA_DIR / "dates.csv"
DATES_OLD_CSV = DATA_DIR / "dates_v12.csv"

IMAGES_ROOT_DIR = ROOT_DIR / Path("images")
IMAGES_BG_DIR = IMAGES_ROOT_DIR / "bg"
IMAGES_DATES_DIR = IMAGES_ROOT_DIR / "dates"
IMAGES_COVERS_DIR = IMAGES_ROOT_DIR / "cover"
IMAGES_CUSTOM_DIR = IMAGES_ROOT_DIR / "custom"

SONG_ROOT_DIR = ROOT_DIR / Path("songs")
DRIVE_DIR = SONG_ROOT_DIR / "drive"
CUSTOM_DIR = SONG_ROOT_DIR / "custom"

LOG_DIR = ROOT_DIR / Path("logs")
