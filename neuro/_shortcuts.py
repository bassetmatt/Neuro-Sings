import os
from pathlib import Path

from neuro import SONGS_CSV, SONGS_DB
from neuro.polars_utils import load_db

DRIVE_NAME = "gdrive"
DL_DIR = Path("songs/drive")

verb = True
V = "-v " if verb else ""
EXC = "--exclude .directory "
OUT = "out"


def drive_pull() -> None:
    os.system(f"rclone sync {V}{DRIVE_NAME}:Neuro {DL_DIR}")


def drive_push() -> None:
    os.system(f"rclone sync {V}--copy-links {EXC}{OUT} {DRIVE_NAME}:Neuro-Custom/")


def dbs_sync() -> None:
    FROM_DB = False
    db = load_db(FROM_DB)
    db.write_csv(SONGS_CSV)
    db.write_database("Songs", f"sqlite:///{SONGS_DB}", if_table_exists="replace")
