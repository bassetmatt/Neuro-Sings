import os
from pathlib import Path

from loguru import logger

from neuro import LOG_DIR, SONGS_CSV, SONGS_DB
from neuro.polars_utils import load_db
from neuro.utils import format_logger

DRIVE_NAME = "gdrive"
DL_DIR = Path("songs/drive")

verb = True
V = "-v " if verb else ""
EXC = "--exclude .directory "
OUT = "out"


def drive_pull() -> None:
    os.system(f"rclone sync {V}{DRIVE_NAME}:Neuro {DL_DIR}")


def drive_push() -> None:
    os.system(f"rclone sync {V}--copy-links {EXC}{OUT} {DRIVE_NAME}:Neuro-Sings/")


def dbs_sync() -> None:
    format_logger(log_file=LOG_DIR / "sync.log")
    FROM_DB = False
    db = load_db(FROM_DB)
    db.write_csv(SONGS_CSV)
    db.write_database("Songs", f"sqlite:///{SONGS_DB}", if_table_exists="replace")
    logger.success(f"Synced versions of the databases, taking {'DB' if FROM_DB else 'CSV'} as source")
