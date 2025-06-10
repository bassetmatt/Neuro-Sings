"""Utility functions for the whole module"""

from __future__ import annotations

import hashlib
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, TextIO

import loguru
from loguru import logger

LOG_FOLDER = Path("logs")
VERBOSE = {
    0: "CRITICAL",
    1: "ERROR",
    2: "WARNING",
    3: "SUCCESS",
    4: "INFO",
    5: "DEBUG",
    6: "TRACE",
}
"""Correspondance for levels of verbosity"""


def rotation_fn(_msg: loguru.Message, file_opened: TextIO) -> bool:
    file = Path(file_opened.name)
    # File is more than 1 week old
    is_old = datetime.now().timestamp() - file.stat().st_ctime > 7 * 86400
    # File is >2MiB
    is_big = file.stat().st_size > (2 << 20)  # Multiplies by 1024 instead of 1000
    return is_old or is_big


def format_logger(*, log_file: Optional[Path] = None, verbosity: int = 5) -> None:
    level = VERBOSE.get(verbosity, "none")
    if level == "none":
        logger.error(f"[CLI] Wrong verbosity {verbosity}")
        raise ValueError("Wrong Level of verbosity, expect int in [0,6]")
    # Adds the segment on multiple lines to disable each at will by commenting
    format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green>"
    format += " | <level>{level:<8}</level>"
    format += " | <level>{message}</level>"

    # Function name is defined separately because it's only used in the logfile to avoid cluttered terminal
    f_name = " | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan>"

    # Resets all previously existing sinks
    logger.remove()

    LOG_FILE = log_file
    if LOG_FILE is None:
        LOG_FILE = LOG_FOLDER.joinpath("neuro.log")
    # Log file
    logger.add(
        LOG_FILE,
        format=format + f_name,
        enqueue=True,
        level=level,
        rotation=rotation_fn,
    )
    logger.info(f"Launched program with command {' '.join(sys.argv)}")

    # Console log
    logger.add(sys.stderr, format=format, level=level, enqueue=True)


# https://stackoverflow.com/questions/22058048/hashing-a-file-in-python
# BUF_SIZE is totally arbitrary, change for your app!
BUF_SIZE = 65536  # lets read stuff in 64kb chunks!


def get_sha256(file: Path) -> str:
    sha256 = hashlib.sha256()
    with open(file, "rb") as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()


def file_check(file_: Path | str, /) -> None:
    file: Path = Path(file_)
    if not file.exists():
        err = f"File '{str(file)}' not found."
        logger.error(err)
        raise FileNotFoundError(err)


def time_format(dt: float, precise: bool = False) -> str:
    """Formats a floating point number of seconds as min/sec, sec, or ms, ...
    Done automatically once and for all

    Args:
        dt (float): Time
        precise (bool, optional): Display seconds if dt > 3600. Display decimals
        if dt>60. Defaults to False.

    Returns:
        str: Pretty time string
    """
    i = int(dt)
    if dt > 3600:
        hour = i // 60
        min, sec = divmod(i, 60)
        extra = f"{sec}s" if precise else ""
        return f"{hour}h{min}mn" + extra
    if dt > 60:
        min, sec = divmod(i, 60)
        extra = f".{dt - i:.2f}" if precise else ""
        return f"{min}mn{sec}s" + extra
    elif dt > 1:
        return f"{dt:.2f}s"
    elif dt > 1e-3:
        return f"{dt * 1e3:.2f} ms"
    elif dt > 1e-6:
        return f"{dt * 1e6:.2f} μs"
    else:
        return f"{dt * 1e9:.2f} ns"
