import os
from pathlib import Path

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
